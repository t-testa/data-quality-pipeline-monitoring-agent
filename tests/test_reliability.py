import json
import os
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

import pytest

from dqagent.contracts import Result
from dqagent.demo import demo_path, load_increment, run_demo, seed
from dqagent.quality import utcnow
from dqagent.store import BusyPipeline


def test_demo_connections_close_deterministically(store, monkeypatch):
    from dqagent.demo import inject

    original = sqlite3.connect
    connections = []

    def connect(*args, **kwargs):
        connection = original(*args, **kwargs)
        connections.append(connection)
        return connection

    monkeypatch.setattr("dqagent.demo.sqlite3.connect", connect)
    seed(store, "success")
    load_increment(store, "success")
    inject(store, "success")
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")


def test_parallel_incremental_load_commits_once(store):
    seed(store, "success")
    with ThreadPoolExecutor(max_workers=4) as pool:
        processed = list(pool.map(lambda _: load_increment(store, "success"), range(8)))
    assert sorted(processed) == [0] * 7 + [100]
    with sqlite3.connect(demo_path(store, "success")) as db:
        assert db.execute("SELECT version FROM checkpoint").fetchone()[0] == 100
        assert db.execute("SELECT COUNT(*) FROM warehouse").fetchone()[0] == 100


def test_wal_reader_survives_writer_and_busy_timeout_is_bounded(store):
    run_id = store.start("locked", "test")
    with store.db() as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE runs SET retries=99 WHERE id=?", (run_id,))
        assert store.run(run_id)["retries"] == 0
        started = time.monotonic()
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            store.start("another", "test")
        assert 4.5 <= time.monotonic() - started < 8
        writer.rollback()
    assert store.run(run_id)["retries"] == 0


def test_sqlite_full_finish_rolls_back_all_results(store, monkeypatch):
    run_id = store.start("full", "test")
    original_db = store.db

    @contextmanager
    def capped_db():
        with original_db() as db:
            pages = db.execute("PRAGMA page_count").fetchone()[0]
            db.execute(f"PRAGMA max_page_count={pages}")
            yield db

    monkeypatch.setattr(store, "db", capped_db)
    result = Result(
        check_id="big",
        name="synthetic",
        table="x",
        kind="row_count",
        executed_at=utcnow(),
        status="pass",
        measured=1,
        expected={},
        details={"synthetic": "x" * 100000},
        duration_ms=0,
    )
    with pytest.raises(sqlite3.OperationalError, match="full"):
        store.finish(run_id, [result])
    monkeypatch.setattr(store, "db", original_db)
    assert store.run(run_id)["status"] == "running"
    assert store.results(run_id) == []
    store.finish(run_id, [], error="Operator verified failed writer stopped")
    assert store.run(run_id)["status"] == "failed"


def test_killed_pipeline_rolls_back_and_requires_explicit_recovery(store, tmp_path):
    run_demo(store, "success")
    marker = tmp_path / "transaction-open.json"
    code = """
import json,sqlite3,sys,time
from pathlib import Path
from dqagent.store import Store
from dqagent.demo import demo_path
store=Store(Path(sys.argv[1]))
run_id=store.start('demo-success','interruption-test')
db=sqlite3.connect(demo_path(store,'success'))
db.execute('BEGIN IMMEDIATE')
db.execute('UPDATE warehouse SET amount=999 WHERE id=1')
db.execute('UPDATE checkpoint SET version=999 WHERE id=1')
Path(sys.argv[2]).write_text(json.dumps({'run_id':run_id}))
time.sleep(60)
"""
    child = subprocess.Popen(
        [sys.executable, "-c", code, str(store.path.parent), str(marker)],
        env={k: v for k, v in os.environ.items() if not k.startswith("DQ_")},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists(), "Synthetic writer did not reach transaction barrier"
        child.kill()
        child.communicate(timeout=5)
        run_id = json.loads(marker.read_text())["run_id"]
        assert store.run(run_id)["status"] == "running"
        with pytest.raises(BusyPipeline):
            store.start("demo-success", "test")
        with sqlite3.connect(demo_path(store, "success")) as db:
            assert db.execute("SELECT amount FROM warehouse WHERE id=1").fetchone()[0] == 100
            assert db.execute("SELECT version FROM checkpoint").fetchone()[0] == 100
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        from unittest.mock import patch

        from dqagent import cli

        with (
            patch.dict(os.environ, {"DQ_DATA_DIR": str(store.path.parent)}),
            patch.object(sys, "argv", ["dqagent", "recover", run_id, "--operator-confirmed-stopped"]),
        ):
            cli.main()
        assert store.run(run_id)["status"] == "failed"
        assert run_demo(store, "success")["records_processed"] == 0
    finally:
        if child.poll() is None:
            child.kill()
        child.communicate(timeout=5)
