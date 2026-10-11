import sqlite3

import pytest
from pydantic import ValidationError

from dqagent.contracts import Rule
from dqagent.demo import SCENARIOS, demo_path, inject, load_increment, rules, run_demo, scenario_demo, seed
from dqagent.quality import QualityEngine, load_rules
from dqagent.source import sqlite_reader
from dqagent.store import BusyPipeline, Store


@pytest.mark.parametrize(
    ("scenario", "check_id", "measured"),
    [
        ("duplicates", "customer_key", 1),
        ("missing_reference", "order_customer", 1),
        ("nulls", "customer_name", 1),
        ("row_decline", "volume_change", 80),
        ("schema_change", "customer_schema", 1),
        ("stale", "customer_freshness", None),
    ],
)
def test_incidents(store, scenario, check_id, measured):
    run = scenario_demo(store, scenario)
    assert run["status"] == "failed"
    result = next(r for r in store.results(run["id"]) if r["check_id"] == check_id)
    assert result["status"] == "failure"
    if measured is not None:
        assert result["measured"] == measured
    else:
        assert result["measured"] >= 167
    assert result["duration_ms"] >= 0
    assert result["executed_at"]


def test_all_check_kinds_healthy_and_idempotent(store):
    first = run_demo(store, "success")
    assert first["records_processed"] == 100
    assert first["status"] == "warning"  # no baseline yet
    second = run_demo(store, "success")
    assert second["status"] == "success"
    assert second["records_processed"] == 0
    assert len(store.results(second["id"])) == 10
    assert all(r["status"] == "pass" for r in store.results(second["id"]))
    assert Store(store.path.parent).run(second["id"]) == second


def test_atomic_rollback_and_retries(store):
    seed(store, "success")
    with pytest.raises(RuntimeError):
        load_increment(store, "success", fail=True)
    with sqlite3.connect(demo_path(store, "success")) as db:
        assert db.execute("SELECT COUNT(*) FROM warehouse").fetchone()[0] == 0
        assert db.execute("SELECT version FROM checkpoint").fetchone()[0] == 0
    run = run_demo(store, "success", fail_attempts=1)
    assert run["retries"] == 1
    assert run["records_processed"] == 100


def test_failure_persists_and_lock_released(store):
    run = run_demo(store, "pipeline_failure", fail_attempts=3)
    assert run["status"] == "failed"
    assert run["retries"] == 2
    assert run["finished_at"]
    assert run_demo(store, "pipeline_failure")["records_processed"] == 100


def test_exclusive_pipeline_and_recovery(store):
    run = store.start("x", "test")
    with pytest.raises(BusyPipeline):
        store.start("x", "test")
    store.finish(run, [], error="Interrupted")
    assert store.start("x", "test") != run


def test_incremental_update_delete_and_no_duplicate_replay(store):
    run_demo(store, "success")
    with sqlite3.connect(demo_path(store, "success")) as db:
        db.execute("UPDATE orders SET amount=150,version=101 WHERE id=1")
        db.execute("UPDATE orders SET deleted=1,version=102 WHERE id=2")
    run = run_demo(store, "success")
    assert run["records_processed"] == 2
    assert run["status"] == "success"
    assert run_demo(store, "success")["records_processed"] == 0
    with sqlite3.connect(demo_path(store, "success")) as db:
        assert db.execute("SELECT COUNT(*) FROM warehouse").fetchone()[0] == 99
        assert db.execute("SELECT amount FROM warehouse WHERE id=1").fetchone()[0] == 150


@pytest.mark.parametrize(
    ("statement", "check_id", "measured"),
    [
        ("UPDATE orders SET amount=-1 WHERE id=1", "order_amount", 1),
        ("UPDATE orders SET cost=200 WHERE id=1", "order_margin", 1),
        ("UPDATE warehouse SET amount=110 WHERE id=1", "order_totals", 10),
        ("DELETE FROM warehouse", "warehouse_rows", 0),
    ],
)
def test_other_quality_failures(store, statement, check_id, measured):
    run_demo(store, "success")
    with sqlite3.connect(demo_path(store, "success")) as db:
        db.execute(statement)
    engine = sqlite_reader(demo_path(store, "success"))
    result = QualityEngine(engine).check(next(r for r in rules() if r.id == check_id))
    engine.dispose()
    assert result.status == "failure"
    assert result.measured == measured


def test_read_only_source(store):
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    engine = sqlite_reader(seed(store, "success"))
    with engine.connect() as conn, pytest.raises(OperationalError):
        conn.execute(text("DELETE FROM customers"))
    engine.dispose()


def test_query_error_redacted(store):
    engine = sqlite_reader(seed(store, "success"))
    result = QualityEngine(engine).check(Rule(id="x", name="x", table="missing", kind="row_count", minimum=1))
    assert result.status == "error"
    assert "SELECT" not in str(result.details)
    engine.dispose()


@pytest.mark.parametrize("bad", ["../NorthstarBI", "NorthstarBI", "success;DROP TABLE customers"])
def test_simulations_isolated(store, bad):
    with pytest.raises(ValueError):
        inject(store, bad)


@pytest.mark.parametrize(
    "extra",
    [
        {"table": "x;DROP TABLE y"},
        {"maximum": -1, "kind": "freshness", "column": "x"},
        {"minimum": 5, "maximum": 1},
        {"raw_sql": "DELETE FROM x"},
    ],
)
def test_invalid_rules(extra):
    with pytest.raises(ValidationError):
        Rule(**({"id": "x", "name": "x", "table": "x", "kind": "row_count", "minimum": 0} | extra))


def test_rule_catalog_validation(tmp_path):
    path = tmp_path / "rules.json"
    path.write_text('[{"id":"x","name":"x","table":"x","kind":"row_count","minimum":1}]')
    assert load_rules(path)[0].id == "x"
    path.write_text("[]")
    with pytest.raises(ValueError):
        load_rules(path)


def test_eight_scenarios_defined():
    assert len(SCENARIOS) == 8
