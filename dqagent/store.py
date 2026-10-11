"""Local durable metadata. One writer per pipeline, bounded read surfaces."""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from dqagent.quality import utcnow


class BusyPipeline(ValueError):
    pass


class Store:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.path = root / "monitoring.sqlite"
        with self.db() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY, pipeline TEXT NOT NULL, started_at TEXT NOT NULL,
                finished_at TEXT, status TEXT NOT NULL, duration_ms REAL,
                records_processed INTEGER NOT NULL DEFAULT 0, retries INTEGER NOT NULL DEFAULT 0,
                error TEXT, origin TEXT NOT NULL);
            CREATE UNIQUE INDEX IF NOT EXISTS single_running ON runs(pipeline) WHERE status='running';
            CREATE INDEX IF NOT EXISTS recent_runs ON runs(pipeline,started_at DESC);
            CREATE TABLE IF NOT EXISTS results (
                id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                check_id TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS run_results ON results(run_id);
            CREATE TABLE IF NOT EXISTS ai_budget (day TEXT PRIMARY KEY, requests INTEGER NOT NULL);
            PRAGMA user_version=1;
            """)

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    def start(self, pipeline, origin):
        run_id = uuid.uuid4().hex
        try:
            with self.db() as db:
                db.execute(
                    "INSERT INTO runs(id,pipeline,started_at,status,origin) VALUES(?,?,?,'running',?)",
                    (run_id, pipeline, utcnow(), origin),
                )
        except sqlite3.IntegrityError as exc:
            raise BusyPipeline(
                "Pipeline already running; inspect and explicitly recover interrupted run"
            ) from exc
        return run_id

    def finish(self, run_id, results, processed=0, retries=0, error=None):
        with self.db() as db:
            run = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not run or run["status"] != "running":
                raise ValueError("Run is not active")
            status = (
                "failed"
                if error or any(r.status in {"failure", "error"} for r in results)
                else "warning"
                if any(r.status == "warning" for r in results)
                else "success"
            )
            now = datetime.now(UTC)
            elapsed = (now - datetime.fromisoformat(run["started_at"])).total_seconds() * 1000
            db.executemany(
                "INSERT INTO results VALUES(?,?,?,?)",
                [(uuid.uuid4().hex, run_id, r.check_id, r.model_dump_json()) for r in results],
            )
            db.execute(
                "UPDATE runs SET finished_at=?,status=?,duration_ms=?,records_processed=?,retries=?,error=? WHERE id=?",
                (now.isoformat(), status, elapsed, processed, retries, error, run_id),
            )

    def runs(self, pipeline=None, limit=50, offset=0):
        limit = max(1, min(limit, 100))
        with self.db() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM runs WHERE (? IS NULL OR pipeline=?) ORDER BY started_at DESC,id DESC LIMIT ? OFFSET ?",
                    (pipeline, pipeline, limit, max(0, offset)),
                )
            ]

    def run(self, run_id):
        with self.db() as db:
            r = db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            return dict(r) if r else None

    def results(self, run_id, limit=100):
        with self.db() as db:
            rows = db.execute(
                "SELECT * FROM results WHERE run_id=? ORDER BY check_id LIMIT ?",
                (run_id, min(100, max(1, limit))),
            )
            return [{"evidence_id": r["id"], "run_id": r["run_id"], **json.loads(r["payload"])} for r in rows]

    def pipelines(self):
        with self.db() as db:
            rows = db.execute("""SELECT pipeline, COUNT(*) run_count,
                MAX(CASE WHEN status='success' THEN finished_at END) last_success,
                MAX(started_at) last_started FROM runs GROUP BY pipeline ORDER BY pipeline LIMIT 100""")
            return [dict(r) for r in rows]

    def baseline(self, pipeline, check_id):
        with self.db() as db:
            row = db.execute(
                """SELECT payload FROM results JOIN runs ON runs.id=results.run_id
                WHERE pipeline=? AND check_id=? AND runs.status IN ('success','warning')
                ORDER BY started_at DESC LIMIT 1""",
                (pipeline, check_id),
            ).fetchone()
            return json.loads(row[0])["details"].get("row_count") if row else None

    def overview(self):
        with self.db() as db:
            statuses = {r[0]: r[1] for r in db.execute("SELECT status,COUNT(*) FROM runs GROUP BY status")}
        latest = [self.runs(p["pipeline"], 1)[0] for p in self.pipelines()]
        results = [r for run in latest for r in self.results(run["id"])]
        return {
            "pipelines": len(latest),
            "run_counts": statuses,
            "pass_rate": round(100 * sum(r["status"] == "pass" for r in results) / len(results), 1)
            if results
            else None,
            "active_issues": sum(r["status"] != "pass" for r in results),
            "freshness": [r for r in results if r["kind"] == "freshness"],
            "scope": "Latest run per pipeline; run counts are all-time; maximum 100 pipelines",
        }

    def reserve_ai(self):
        day = datetime.now(UTC).date().isoformat()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT OR IGNORE INTO ai_budget VALUES(?,0)", (day,))
            count = db.execute("SELECT requests FROM ai_budget WHERE day=?", (day,)).fetchone()[0]
            if count >= 20:
                return False
            db.execute("UPDATE ai_budget SET requests=requests+1 WHERE day=?", (day,))
            return True
