"""Exercise compose.local.yaml on new synthetic volumes; never deploy over existing history."""

import asyncio
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

from scripts.local_snapshot import operate


def main():
    root = Path(__file__).resolve().parents[1]
    project = "nwlocaltest" + uuid.uuid4().hex[:8]
    folder = root / ".local" / project
    folder.mkdir(parents=True)
    read_token, diagnostic_token = secrets.token_urlsafe(40), secrets.token_urlsafe(40)
    env_file = folder / ".env"
    with os.fdopen(os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w") as out:
        out.write(f"DQ_API_TOKEN={read_token}\nDQ_DIAGNOSTIC_TOKEN={diagnostic_token}\n")
    override = folder / "override.yaml"
    override.write_text(
        "services:\n  monitor:\n    env_file: !override [" + json.dumps(str(env_file)) + "]\n"
        '    ports: !override ["127.0.0.1::8765"]\n',
        encoding="utf-8",
    )
    source_volume, restore_volume = project + "_source", project + "_restored"
    image = "northwatch-local:candidate"
    env = {**os.environ, "NORTHWATCH_DATA_VOLUME": source_volume, "NORTHWATCH_LOCAL_IMAGE": image}
    compose = [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        str(root / "compose.local.yaml"),
        "-f",
        str(override),
    ]

    def command(*args):
        result = subprocess.run(args, cwd=root, env=env, capture_output=True, text=True, check=False)
        if result.returncode:
            # No environment, credentials or raw command output in errors.
            raise RuntimeError("Isolated local acceptance command failed: " + args[0])
        return result.stdout.strip()

    def request(path, body=None):
        req = urllib.request.Request(
            base + path,
            data=json.dumps(body).encode() if body else None,
            headers={"Authorization": "Bearer " + read_token, "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.load(response)

    def snapshot():
        return [request("/api/runs/" + r["id"]) for r in request("/api/runs?limit=100")]

    report = {
        "project": project,
        "image": image,
        "source_volume": source_volume,
        "restore_volume": restore_volume,
        "checks": {},
    }
    try:
        command("docker", "volume", "create", source_volume)
        config = json.loads(command(*compose, "config", "--format", "json"))
        service = config["services"]["monitor"]
        assert service["restart"] == "unless-stopped" and service["read_only"]
        assert service["environment"]["DQ_OPENAI_API_KEY"] == service["environment"]["DQ_OPENAI_MODEL"] == ""
        assert service["environment"]["DQ_SOURCE_URL"] == ""
        assert service["pids_limit"] == 128 and service["healthcheck"]["retries"] == 3
        assert config["networks"]["local-only"]["driver"] == "bridge"
        command(*compose, "up", "-d", "--no-build", "--wait")
        base = "http://" + command(*compose, "port", "monitor", "8765")
        assert base.startswith("http://127.0.0.1:")
        assert request("/ready") == {"status": "ready"} and request("/api/runs") == []
        report["checks"]["fresh_local_compose_and_cost_controls"] = "PASS"
        for scenario in ("success", "duplicates"):
            command(*compose, "exec", "-T", "monitor", "python", "-m", "dqagent.cli", "demo", scenario)
        before = snapshot()
        incident = next(
            p for p in before if p["run"]["pipeline"] == "demo-duplicates" and p["run"]["status"] == "failed"
        )
        run = incident["run"]
        diagnosis = request(
            "/api/diagnose",
            {
                "pipeline": run["pipeline"],
                "run_id": run["id"],
                "question": "Explain recorded duplicates",
                "use_ai": False,
            },
        )
        check = next(f for f in diagnosis["facts"] if f.get("check_id") == "customer_key")
        assert check["measured"] == 1 and check["expected"]["tolerance"] == 0

        async def mcp_check():
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "dqagent.mcp_server"],
                env={"DQ_MCP_TOKEN": read_token, "DQ_MCP_API_URL": base},
            )
            async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                assert len((await session.list_tools()).tools) == 9
                result = await session.call_tool(
                    "get_incident_details", {"pipeline": run["pipeline"], "run_id": run["id"], "limit": 100}
                )
                assert not result.isError
                payload = result.structuredContent or json.loads(result.content[0].text)
                assert payload["data"]["run"]["id"] == run["id"]

        asyncio.run(mcp_check())
        report["checks"]["deterministic_evidence_and_nine_stdio_mcp_tools"] = "PASS"
        container = command(*compose, "ps", "-q", "monitor")
        # PID-namespace init ignores an in-namespace SIGKILL. Uvicorn handles
        # SIGTERM, so trigger an actual process exit without Docker's manual-stop flag.
        command("docker", "exec", container, "python", "-c", "import os,signal; os.kill(1,signal.SIGTERM)")
        started = time.monotonic()
        while time.monotonic() - started < 45:
            state = json.loads(command("docker", "inspect", container, "--format", "{{json .State}}"))
            if (
                state.get("Health", {}).get("Status") == "healthy"
                and int(command("docker", "inspect", container, "--format", "{{.RestartCount}}")) > 0
            ):
                # Docker Desktop can reassign an ephemeral host port on restart.
                base = "http://" + command(*compose, "port", "monitor", "8765")
                assert base.startswith("http://127.0.0.1:")
                try:
                    if request("/ready") == {"status": "ready"}:
                        break
                except (urllib.error.URLError, OSError):
                    pass
            time.sleep(1)
        else:
            raise AssertionError("Automatic process restart did not become healthy")
        assert snapshot() == before
        report["checks"]["automatic_restart_and_exact_history"] = "PASS"
        report["restart_seconds"] = round(time.monotonic() - started, 3)
        archive = folder / "backups" / "snapshot.tar.gz"
        try:
            operate("backup", source_volume, archive, image)
        except ValueError as exc:
            assert "Stop all" in str(exc)
        else:
            raise AssertionError("Running-volume backup guard failed")
        command(*compose, "stop")
        report["backup"] = operate("backup", source_volume, archive, image)
        report["restore"] = operate("restore", restore_volume, archive, image)
        command(*compose, "down")  # External volume is retained; no --volumes.
        env["NORTHWATCH_DATA_VOLUME"] = restore_volume
        command(*compose, "up", "-d", "--no-build", "--wait")
        base = "http://" + command(*compose, "port", "monitor", "8765")
        assert snapshot() == before
        replay = json.loads(
            command(*compose, "exec", "-T", "monitor", "python", "-m", "dqagent.cli", "demo", "duplicates")
        )
        # The CLI prints a list of the baseline/final executions for this scenario.
        replay_rows = replay if isinstance(replay, list) else [replay]
        assert all(r["records_processed"] == 0 for r in replay_rows)
        report["checks"]["full_volume_restore_fresh_service_exact_evidence_and_checkpoint"] = "PASS"
        report["preserved_fixture_runs"] = len(before)
        report["fixture_history_sha256"] = hashlib.sha256(
            json.dumps(before, sort_keys=True).encode()
        ).hexdigest()
    finally:
        command(*compose, "down")
        (root / "artifacts" / "local-deployment-acceptance.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
