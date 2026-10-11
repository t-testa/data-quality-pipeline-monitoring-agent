import asyncio
import json
import logging
import sqlite3
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from dqagent.contracts import Question
from dqagent.demo import scenario_demo
from dqagent.diagnostics import ask_model, diagnose
from dqagent.logging_utils import install_redaction
from dqagent.mcp_server import make_server
from dqagent.source import sqlserver_reader, verify_readonly_identity
from scripts.backup import backup


@pytest.mark.parametrize(
    "options",
    [
        "Encrypt=yes&TrustServerCertificate=yes",
        "Encrypt=yes&trustservercertificate=true",
        "Encrypt=yes&Encrypt=no",
        "Encrypt=yes&encrypt=no",
        "Encrypt=yes&odbc_connect=DRIVER%3Dx%3BEncrypt%3Dno",
        "Encrypt=yes&driver=x%3BTrustServerCertificate%3Dyes",
        "Encrypt=yes&foo%3BEncrypt%3Dno=x",
    ],
)
def test_sql_tls_override_rejected(options):
    with pytest.raises(ValueError):
        sqlserver_reader("mssql+pyodbc://host/db?" + options)


def test_sql_tls_validated_and_bounded(monkeypatch):
    engine = MagicMock()
    create = MagicMock(return_value=engine)
    monkeypatch.setattr("dqagent.source.create_engine", create)
    monkeypatch.setattr("dqagent.source.event.listens_for", lambda *_: lambda fn: fn)
    assert sqlserver_reader("mssql+pyodbc://host/db?Encrypt=yes&TrustServerCertificate=no") is engine
    assert create.call_args.kwargs["max_overflow"] == 0


@pytest.mark.parametrize("permission", ["INSERT", "UPDATE", "DELETE", "ALTER", "CONTROL", "TAKE OWNERSHIP"])
def test_each_sql_write_permission_is_rejected(permission):
    from dqagent.demo import rules

    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.scalar.side_effect = lambda sql, args=None: (
        int(args["permission"] == permission) if args else int("'SELECT'" in str(sql))
    )
    with pytest.raises(PermissionError):
        verify_readonly_identity(engine, rules())


def test_provider_destination_and_limits(settings, monkeypatch):
    provider = MagicMock()
    provider.return_value.__enter__.return_value.responses.parse.return_value.output_parsed = "ok"
    transport = MagicMock()
    monkeypatch.setattr("openai.OpenAI", provider)
    monkeypatch.setattr("httpx.Client", transport)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://untrusted.invalid")
    assert ask_model(settings, "why", {}) == "ok"
    assert provider.call_args.kwargs["base_url"] == "https://api.openai.com/v1"
    assert provider.call_args.kwargs["timeout"] == 20
    assert provider.call_args.kwargs["max_retries"] == 0
    assert transport.call_args.kwargs == {"trust_env": False, "follow_redirects": False}


def test_question_secrets_removed_before_provider(store, settings):
    run = scenario_demo(store, "duplicates")
    settings.openai_api_key = SecretStr("synthetic-private-api-value")
    settings.openai_model = "offline-test"

    def provider(_, question, evidence):
        for value in ("r" * 40, "synthetic-private-api-value", "synthetic-password"):
            assert value not in question
        return {"evidence_ids": [run["id"]], "guidance": []}

    result = diagnose(
        store,
        settings,
        Question(
            pipeline=run["pipeline"],
            use_ai=True,
            question="r" * 40 + " synthetic-private-api-value password=synthetic-password",
        ),
        provider,
    )
    assert result["ai_status"].startswith("available")


def test_sdk_child_logs_do_not_propagate_secrets(settings, caplog):
    install_redaction(settings)
    with caplog.at_level(logging.DEBUG):
        logging.getLogger("openai._base_client").debug("SYNTHETIC_PROVIDER_SECRET")
        logging.getLogger("httpx").warning("SYNTHETIC_PROVIDER_SECRET")
    assert "SYNTHETIC_PROVIDER_SECRET" not in caplog.text


def test_request_observability_excludes_input(client, headers, caplog):
    with caplog.at_level(logging.INFO, logger="dqagent"):
        response = client.get("/api/runs?pipeline=SYNTHETIC_PRIVATE_VALUE", headers=headers)
    events = [json.loads(r.message) for r in caplog.records if r.name == "dqagent"]
    assert events[-1]["route"] == "/api/runs"
    assert events[-1]["status"] == 200
    assert events[-1]["request_id"] == response.headers["X-Request-ID"]
    assert "SYNTHETIC_PRIVATE_VALUE" not in caplog.text
    assert headers["Authorization"] not in caplog.text


def test_readiness_reports_low_disk_space(client, monkeypatch):
    monkeypatch.setattr("dqagent.api.shutil.disk_usage", lambda _: SimpleNamespace(free=0))
    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 200


@pytest.mark.parametrize("suffix", ["?token=private", "#private", ""])
def test_mcp_api_url_credentials_rejected(monkeypatch, suffix):
    monkeypatch.setenv("DQ_MCP_TOKEN", "r" * 40)
    url = "https://user:private@example.invalid" if not suffix else "https://example.invalid" + suffix
    monkeypatch.setenv("DQ_MCP_API_URL", url)
    with pytest.raises(ValueError):
        make_server()


def test_mcp_response_byte_limit(monkeypatch):
    monkeypatch.setenv("DQ_MCP_TOKEN", "r" * 40)
    client = MagicMock()
    response = client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value
    response.status_code = 200
    response.iter_bytes.return_value = [b" " * 262144, b" "]
    monkeypatch.setattr("dqagent.mcp_server.httpx.Client", client)
    with pytest.raises(Exception, match="response limit"):
        asyncio.run(make_server().call_tool("list_pipelines", {}))


def test_backup_integrity_and_no_overwrite(store, tmp_path):
    scenario_demo(store, "duplicates")
    destination = tmp_path / "backup.sqlite"
    backup(store.path, destination)
    with store.db() as source, sqlite3.connect(destination) as restored:
        assert list(source.iterdump()) == list(restored.iterdump())
    original = destination.read_bytes()
    with pytest.raises(FileExistsError):
        backup(store.path, destination)
    assert destination.read_bytes() == original


def test_corrupt_backup_is_not_retained(tmp_path):
    source, destination = tmp_path / "bad.sqlite", tmp_path / "backup.sqlite"
    source.write_bytes(b"invalid sqlite database")
    with pytest.raises(sqlite3.DatabaseError):
        backup(source, destination)
    assert not destination.exists()
