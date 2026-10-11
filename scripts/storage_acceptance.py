"""Synthetic growth/backup exercise; never uses operator settings or monitoring history."""

import hashlib
import json
import shutil
import sqlite3
import tempfile
import time
from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient

from dqagent.api import create_app
from dqagent.contracts import Result
from dqagent.demo import rules
from dqagent.quality import utcnow
from dqagent.settings import Settings
from dqagent.store import Store
from scripts.backup import backup


def main():
    Path(".local").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="storage-acceptance-", dir=".local") as directory:
        root = Path(directory)
        store = Store(root / "history")
        rows = [
            Result(
                check_id=r.id,
                name=r.name,
                table=r.table,
                kind=r.kind,
                executed_at=utcnow(),
                status="pass",
                measured=0,
                expected=r.model_dump(exclude_none=True),
                duration_ms=0,
            )
            for r in rules()
        ]
        started = time.monotonic()
        for _ in range(1000):
            run_id = store.start("growth-sample", "synthetic-capacity-test")
            store.finish(run_id, rows)
        elapsed = time.monotonic() - started
        with store.db() as db:
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            source_hash = hashlib.sha256("\n".join(db.iterdump()).encode()).hexdigest()
        size = store.path.stat().st_size
        started = time.monotonic()
        backup(store.path, root / "backup.sqlite")
        with closing(sqlite3.connect(root / "backup.sqlite")) as restored:
            restored_hash = hashlib.sha256("\n".join(restored.iterdump()).encode()).hexdigest()
            assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert restored.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1000
            assert restored.execute("SELECT COUNT(*) FROM results").fetchone()[0] == 10000
        assert source_hash == restored_hash
        restored_root = root / "restored-application"
        restored_root.mkdir()
        shutil.copyfile(root / "backup.sqlite", restored_root / "monitoring.sqlite")
        settings = Settings(
            _env_file=None,
            data_dir=restored_root,
            api_token="r" * 40,
            diagnostic_token="d" * 40,
            openai_api_key="",
            openai_model="",
            source_url="",
        )
        with TestClient(create_app(settings)) as client:
            assert client.get("/ready").status_code == 200
            response = client.get("/api/runs/" + run_id, headers={"Authorization": "Bearer " + "r" * 40})
            assert response.status_code == 200
            assert response.json()["run"] == store.run(run_id)
            assert response.json()["results"] == store.results(run_id)
        recovery_seconds = time.monotonic() - started
        assert recovery_seconds < 60
        report = {
            "runs": 1000,
            "checks": 10000,
            "database_bytes": size,
            "bytes_per_run_including_ten_checks": size / 1000,
            "write_seconds": round(elapsed, 3),
            "backup_restore_verification_seconds": round(recovery_seconds, 3),
            "logical_sha256": source_hash,
            "integrity": "ok",
            "contents_match": True,
            "fresh_application_from_restored_copy": "PASS",
            "scope": "Synthetic local capacity sample; no retention deletion; not an Azure benchmark",
        }
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/hardening-storage.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
