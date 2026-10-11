"""One-time integrated Windows discovery validation; never configures a scheduled admin connection."""

from pathlib import Path

from sqlalchemy import URL, text

from dqagent.quality import QualityEngine, load_rules
from dqagent.source import sqlserver_reader
from dqagent.store import Store

url = URL.create(
    "mssql+pyodbc",
    host="localhost",
    database="NorthstarBI",
    query={
        "driver": "ODBC Driver 18 for SQL Server",
        "Encrypt": "yes",
        "TrustServerCertificate": "yes",
        "Trusted_Connection": "yes",
    },
)
engine = sqlserver_reader(url.render_as_string(hide_password=False))
store = Store(Path("data"))
run_id = store.start("northstar-discovery", "one-time-Windows-identity-read-only-queries")
results = []
try:
    with engine.connect() as conn:
        print("Connected database:", conn.scalar(text("SELECT DB_NAME()")))
        print("Current identity is sysadmin:", conn.scalar(text("SELECT IS_SRVROLEMEMBER('sysadmin')")))
    results = [
        QualityEngine(engine).check(r, store.baseline("northstar-discovery", r.id))
        for r in load_rules(Path("dqagent/rules/northstar.json"))
    ]
    store.finish(run_id, results)
    print("Run:", run_id)
    for result in results:
        print(result.check_id, result.status, result.measured)
finally:
    engine.dispose()
