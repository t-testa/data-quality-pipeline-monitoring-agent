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
