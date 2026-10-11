"""Validate the approved source with the same least-privilege gate as the CLI."""

from pathlib import Path

from dqagent.quality import QualityEngine, load_rules
from dqagent.settings import Settings
from dqagent.source import sqlserver_reader, verify_readonly_identity
from dqagent.store import Store

settings = Settings()
engine = sqlserver_reader(settings.source_url.get_secret_value())
try:
    rules = load_rules(Path("dqagent/rules/northstar.json"))
    verify_readonly_identity(engine, rules)
    store = Store(settings.data_dir)
    run_id = store.start("northstar-discovery", "external-read-only-validation")
    results = [QualityEngine(engine).check(r, store.baseline("northstar-discovery", r.id)) for r in rules]
    store.finish(run_id, results)
    print("Run:", run_id)
    for result in results:
        print(result.check_id, result.status, result.measured)
finally:
    engine.dispose()
