"""Synthetic data only. This module never accepts a database URL or arbitrary path."""

import sqlite3
import time
from datetime import UTC, datetime, timedelta

from dqagent.contracts import Kind, Rule
from dqagent.quality import QualityEngine
from dqagent.source import sqlite_reader

SCENARIOS = (
    "success",
    "duplicates",
    "missing_reference",
    "nulls",
    "row_decline",
    "stale",
    "pipeline_failure",
    "schema_change",
)


def demo_path(store, scenario):
    if scenario not in SCENARIOS:
        raise ValueError("Unknown isolated demo scenario")
    folder = store.path.parent / "demo"
    folder.mkdir(exist_ok=True)
    return folder / f"{scenario}.sqlite"


def seed(store, scenario):
    path = demo_path(store, scenario)
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS customers (id INTEGER NOT NULL, name VARCHAR(80), updated_at DATETIME NOT NULL);
        CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL,
            amount DECIMAL(12,2) NOT NULL, cost DECIMAL(12,2) NOT NULL, updated_at DATETIME NOT NULL,
            version INTEGER NOT NULL, deleted INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS warehouse (id INTEGER PRIMARY KEY, amount DECIMAL(12,2) NOT NULL);
        CREATE TABLE IF NOT EXISTS checkpoint (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS simulation (id INTEGER PRIMARY KEY CHECK(id=1));
        INSERT OR IGNORE INTO checkpoint VALUES(1,0);
        """)
        if db.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
            now = datetime.now(UTC).isoformat()
            db.executemany(
                "INSERT INTO customers VALUES(?,?,?)",
                [(i, f"Synthetic customer {i}", now) for i in range(1, 11)],
            )
            db.executemany(
                "INSERT INTO orders VALUES(?,?,?,?,?,?,0)",
                [(i, (i - 1) % 10 + 1, 100, 60, now, i) for i in range(1, 101)],
            )
    return path


def inject(store, scenario):
    """Idempotent fixture mutation confined to a generated demo path."""
    path = seed(store, scenario)
    with sqlite3.connect(path) as db:
        if db.execute("SELECT COUNT(*) FROM simulation").fetchone()[0]:
            return
        if scenario == "duplicates":
            db.execute("INSERT INTO customers SELECT * FROM customers WHERE id=1")
        elif scenario == "missing_reference":
            db.execute("UPDATE orders SET customer_id=999,version=101 WHERE id=1")
        elif scenario == "nulls":
            db.execute("UPDATE customers SET name=NULL WHERE id=1")
        elif scenario == "row_decline":
            # Explicit tombstones represent source deletions, not lost high-watermark rows.
            db.execute("UPDATE orders SET deleted=1,version=100+id WHERE id>20")
        elif scenario == "stale":
            db.execute(
                "UPDATE customers SET updated_at=?", ((datetime.now(UTC) - timedelta(days=7)).isoformat(),)
            )
        elif scenario == "schema_change":
            db.execute("ALTER TABLE customers ADD COLUMN unexpected VARCHAR(20)")
        db.execute("INSERT INTO simulation VALUES(1)")


def rules():
    configs = [
        dict(
            id="customer_name", name="Required customer name", table="customers", kind="null", column="name"
        ),
        dict(id="customer_key", name="Unique customer ID", table="customers", kind="duplicate", column="id"),
        dict(
            id="order_customer",
            name="Order customer exists",
            table="orders",
            kind="reference",
            column="customer_id",
            other_table="customers",
            other_column="id",
        ),
        dict(
            id="warehouse_rows", name="Warehouse minimum rows", table="warehouse", kind="row_count", minimum=1
        ),
        dict(
            id="customer_freshness",
            name="Customer freshness hours",
            table="customers",
            kind="freshness",
            column="updated_at",
            maximum=24,
        ),
        dict(
            id="order_amount",
            name="Nonnegative order amount",
            table="orders",
            kind="numeric_range",
            column="amount",
            minimum=0,
            maximum=10000,
        ),
        dict(
            id="customer_schema",
            name="Customer schema contract",
            table="customers",
            kind="schema",
            expected_schema={"id": "integer!", "name": "text?", "updated_at": "datetime!"},
        ),
        dict(
            id="order_totals",
            name="Loaded order reconciliation",
            table="active_orders",
            kind="reconciliation",
            column="amount",
            other_table="warehouse",
            other_column="amount",
            tolerance=0.01,
        ),
        dict(
            id="order_margin",
            name="Cost does not exceed amount",
            table="orders",
            kind="business_rule",
            column="cost",
            other_column="amount",
            operator="le",
        ),
        dict(
            id="volume_change",
            name="Warehouse volume change percent",
            table="warehouse",
            kind="anomaly",
            maximum=30,
        ),
    ]
    return [Rule(**c) for c in configs]


def load_increment(store, scenario, fail=False):
    path = seed(store, scenario)
    with sqlite3.connect(path, timeout=5) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE VIEW IF NOT EXISTS active_orders AS SELECT id,amount FROM orders WHERE deleted=0")
        watermark = db.execute("SELECT version FROM checkpoint WHERE id=1").fetchone()[0]
        rows = db.execute(
            "SELECT id,amount,version,deleted FROM orders WHERE version>? ORDER BY version,id", (watermark,)
        ).fetchall()
        for row in rows:
            if row[3]:
                db.execute("DELETE FROM warehouse WHERE id=?", (row[0],))
            else:
                db.execute(
                    "INSERT INTO warehouse VALUES(?,?) ON CONFLICT(id) DO UPDATE SET amount=excluded.amount",
                    row[:2],
                )
        if fail:
            raise RuntimeError("simulated_failure")
        if rows:
            db.execute("UPDATE checkpoint SET version=? WHERE id=1", (max(r[2] for r in rows),))
        return len(rows)


def run_demo(store, scenario, fail_attempts=0, max_retries=2):
    if not 0 <= max_retries <= 3 or not 0 <= fail_attempts <= 4:
        raise ValueError("Retry bounds exceeded")
    path = seed(store, scenario)
    pipeline = f"demo-{scenario}"
    run_id = store.start(pipeline, "isolated-demo")
    processed, retries, error, results = 0, 0, None, []
    try:
        for attempt in range(max_retries + 1):
            try:
                processed = load_increment(store, scenario, fail=attempt < fail_attempts)
                break
            except (sqlite3.OperationalError, RuntimeError):
                if attempt == max_retries:
                    raise
                retries += 1
                time.sleep(0.05 * 2**attempt)
        engine = sqlite_reader(path)
        try:
            results = [
                QualityEngine(engine).check(
                    r, store.baseline(pipeline, r.id) if r.kind == Kind.anomaly else None
                )
                for r in rules()
            ]
        finally:
            engine.dispose()
    except Exception:
        error = "Pipeline load failed after bounded retries; no source error text retained"
    store.finish(run_id, results, processed, retries, error)
    return store.run(run_id)


def scenario_demo(store, scenario):
    # Establish baseline before injecting an incident. Repeated calls do not reset data.
    if not store.runs(f"demo-{scenario}", 1):
        run_demo(store, scenario)
    inject(store, scenario)
    return run_demo(store, scenario, fail_attempts=3 if scenario == "pipeline_failure" else 0)
