"""Only SQLAlchemy-generated SELECTs; no SQL string input or source DDL/DML."""

from pathlib import Path

from sqlalchemy import create_engine, event


def sqlite_reader(path: Path):
    if not path.is_file():
        raise ValueError("Source does not exist")
    engine = create_engine(f"sqlite:///file:{path.resolve().as_posix()}?mode=ro&uri=true")

    @event.listens_for(engine, "connect")
    def readonly(connection, _):
        connection.execute("PRAGMA query_only=ON")
        # Stop pathological queries after a bounded number of VM operations.
        import time

        deadline = [0.0]
        connection.set_trace_callback(lambda _: deadline.__setitem__(0, time.monotonic() + 10))
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline[0]), 10000)

    return engine


def verify_readonly_identity(engine, rules):
    """Fail closed on elevated identities or write permissions on monitored objects."""
    from sqlalchemy import text

    with engine.connect() as conn:
        elevated = conn.scalar(
            text(
                "SELECT CASE WHEN IS_SRVROLEMEMBER('sysadmin')=1 OR IS_MEMBER('db_owner')=1 OR IS_MEMBER('db_ddladmin')=1 THEN 1 ELSE 0 END"
            )
        )
        if elevated != 0:
            raise PermissionError("Use a dedicated least-privilege source identity")
        objects = {(r.schema_name or "dbo", r.table) for r in rules}
        objects |= {(r.schema_name or "dbo", r.other_table) for r in rules if r.other_table}
        for schema, table in objects:
            for permission in ("INSERT", "UPDATE", "DELETE", "ALTER", "CONTROL", "TAKE OWNERSHIP"):
                value = conn.scalar(
                    text("SELECT HAS_PERMS_BY_NAME(:object, 'OBJECT', :permission)"),
                    {"object": f"{schema}.{table}", "permission": permission},
                )
                if value != 0:
                    raise PermissionError("Source write permissions or unresolved object detected")
            if (
                conn.scalar(
                    text("SELECT HAS_PERMS_BY_NAME(:object, 'OBJECT', 'SELECT')"),
                    {"object": f"{schema}.{table}"},
                )
                != 1
            ):
                raise PermissionError("Source SELECT permission required")


def sqlserver_reader(url: str):
    from sqlalchemy.engine import make_url

    parsed = make_url(url)
    if parsed.drivername != "mssql+pyodbc":
        raise ValueError("Only mssql+pyodbc is supported for external sources")
    if str(parsed.query.get("Encrypt", "")).lower() not in {"yes", "true", "mandatory"}:
        raise ValueError("SQL Server connections must explicitly enable Encrypt=yes")
    engine = create_engine(
        parsed, pool_size=2, max_overflow=0, pool_timeout=3, pool_pre_ping=True, connect_args={"timeout": 5}
    )

    @event.listens_for(engine, "connect")
    def timeout(connection, _):
        connection.timeout = 10

    return engine
