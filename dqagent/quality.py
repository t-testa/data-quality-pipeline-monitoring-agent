import json
import time
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import MetaData, Table, and_, exists, func, inspect, or_, select

from dqagent.contracts import Kind, Result, Rule


def utcnow():
    return datetime.now(UTC).isoformat()


def load_rules(path: Path) -> list[Rule]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not 1 <= len(raw) <= 100:
        raise ValueError("Supply 1–100 rules")
    rules = [Rule.model_validate(item) for item in raw]
    if len({r.id for r in rules}) != len(rules):
        raise ValueError("Check IDs must be unique")
    return rules


def type_family(t):
    name = str(t).upper()
    if "INT" in name or "BOOL" in name or "BIT" in name:
        return "integer"
    if any(x in name for x in ("NUM", "DEC", "REAL", "FLOAT", "DOUBLE")):
        return "numeric"
    if "DATE" in name or "TIME" in name:
        return "datetime"
    if "CHAR" in name or "TEXT" in name:
        return "text"
    return name.lower()


class QualityEngine:
    def __init__(self, engine):
        self.engine = engine

    def check(self, rule: Rule, baseline: float | None = None) -> Result:
        start = time.perf_counter()
        status, value, affected, details = "pass", None, None, {}
        expected = rule.model_dump(mode="json", exclude={"id", "name", "table", "kind"}, exclude_none=True)
        try:
            with self.engine.connect() as conn:
                table = Table(rule.table, MetaData(), schema=rule.schema_name, autoload_with=conn)
                col = table.c[rule.column] if rule.column else None

                def count(condition):
                    return conn.scalar(select(func.count()).select_from(table).where(condition))

                bad = False
                if rule.kind == Kind.null:
                    value = affected = count(col.is_(None))
                    bad = value > rule.tolerance
                elif rule.kind == Kind.duplicate:
                    groups = (
                        select(func.count().label("n"))
                        .select_from(table)
                        .group_by(col)
                        .having(func.count() > 1)
                        .subquery()
                    )
                    value = affected = conn.scalar(select(func.coalesce(func.sum(groups.c.n - 1), 0)))
                    bad = value > rule.tolerance
                elif rule.kind == Kind.reference:
                    other = Table(rule.other_table, MetaData(), schema=rule.schema_name, autoload_with=conn)
                    value = affected = count(
                        and_(col.is_not(None), ~exists(select(1).where(other.c[rule.other_column] == col)))
                    )
                    bad = value > rule.tolerance
                elif rule.kind in {Kind.row_count, Kind.anomaly}:
                    rows = conn.scalar(select(func.count()).select_from(table))
                    if rule.kind == Kind.row_count:
                        value = rows
                        bad = (rule.minimum is not None and rows < rule.minimum) or (
                            rule.maximum is not None and rows > rule.maximum
                        )
                    else:
                        details = {"row_count": rows, "baseline": baseline}
                        if baseline is None:
                            status, details["reason"] = "warning", "No prior completed baseline"
                        elif baseline == 0:
                            value = 0 if rows == 0 else 100
                            bad = value > rule.maximum
                        else:
                            value = abs(rows - baseline) / baseline * 100
                            bad = value > rule.maximum
                elif rule.kind == Kind.freshness:
                    latest = conn.scalar(select(func.max(col)))
                    if latest is None:
                        bad, details = True, {"reason": "No non-null freshness timestamp"}
                    else:
                        stamp = (
                            datetime.fromisoformat(str(latest)) if isinstance(latest, str | date) else latest
                        )
                        stamp = stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp.astimezone(UTC)
                        value = (datetime.now(UTC) - stamp).total_seconds() / 3600
                        bad = value < -0.1 or value > rule.maximum
                elif rule.kind == Kind.numeric_range:
                    conditions = [col.is_(None)]
                    if rule.minimum is not None:
                        conditions.append(col < rule.minimum)
                    if rule.maximum is not None:
                        conditions.append(col > rule.maximum)
                    value = affected = count(or_(*conditions))
                    bad = value > rule.tolerance
                elif rule.kind == Kind.schema:
                    columns = inspect(conn).get_columns(rule.table, schema=rule.schema_name)
                    actual = {
                        c["name"]: type_family(c["type"]) + ("?" if c["nullable"] else "!") for c in columns
                    }
                    added = sorted(actual.keys() - rule.expected_schema.keys())
                    removed = sorted(rule.expected_schema.keys() - actual.keys())
                    changed = sorted(
                        k
                        for k in actual.keys() & rule.expected_schema.keys()
                        if actual[k] != rule.expected_schema[k]
                    )
                    value = len(added) + len(removed) + len(changed)
                    details = {"added": added, "removed": removed, "changed": changed}
                    bad = value > 0
                elif rule.kind == Kind.reconciliation:
                    other = Table(rule.other_table, MetaData(), schema=rule.schema_name, autoload_with=conn)
                    left = conn.scalar(select(func.coalesce(func.sum(col), 0)))
                    right = conn.scalar(select(func.coalesce(func.sum(other.c[rule.other_column]), 0)))
                    value = float(abs(left - right))
                    details = {"source_total": float(left), "comparison_total": float(right)}
                    bad = value > rule.tolerance
                elif rule.kind == Kind.business_rule:
                    right = table.c[rule.other_column]
                    predicate = {"le": col <= right, "ge": col >= right, "eq": col == right}[rule.operator]
                    value = affected = count(or_(col.is_(None), right.is_(None), ~predicate))
                    bad = value > rule.tolerance
                if bad:
                    status = rule.severity
        except Exception:
            # DB exceptions can embed SQL, credentials and source values. Never persist raw messages.
            status, details = (
                "error",
                {"reason": "Check execution failed; verify connectivity, permissions and schema"},
            )
        return Result(
            check_id=rule.id,
            name=rule.name,
            table=rule.table,
            kind=rule.kind,
            executed_at=utcnow(),
            status=status,
            measured=value,
            expected=expected,
            affected_records=affected,
            details=details,
            duration_ms=round((time.perf_counter() - start) * 1000, 3),
        )
