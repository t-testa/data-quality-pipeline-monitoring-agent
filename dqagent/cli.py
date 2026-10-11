import argparse
import json
import secrets
from pathlib import Path

from dqagent.demo import SCENARIOS, scenario_demo
from dqagent.quality import QualityEngine, load_rules
from dqagent.settings import Settings
from dqagent.source import sqlserver_reader
from dqagent.store import Store


def main():
    parser = argparse.ArgumentParser(description="Private data quality monitoring")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    demo = sub.add_parser("demo")
    demo.add_argument("scenario", choices=["all", *SCENARIOS])
    sub.add_parser("serve")
    check = sub.add_parser("check-source")
    check.add_argument("--rules", type=Path, required=True)
    check.add_argument("--pipeline", default="northstar-quality")
    recover = sub.add_parser("recover")
    recover.add_argument("run_id")
    recover.add_argument("--operator-confirmed-stopped", action="store_true", required=True)
    args = parser.parse_args()
    if args.command == "init":
        path = Path(".env")
        with path.open("x", encoding="utf-8") as f:
            f.write(
                f"DQ_API_TOKEN={secrets.token_urlsafe(32)}\nDQ_DIAGNOSTIC_TOKEN={secrets.token_urlsafe(32)}\nDQ_DATA_DIR=data\n"
            )
        print("Created .env with unique local tokens; keep it private.")
        return
    settings = Settings()
    store = Store(settings.data_dir)
    if args.command == "demo":
        for scenario in SCENARIOS if args.scenario == "all" else [args.scenario]:
            print(json.dumps(scenario_demo(store, scenario)))
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("dqagent.api:create_app", factory=True, host="127.0.0.1", port=8765, access_log=False)
    elif args.command == "recover":
        store.finish(
            args.run_id, [], error="Operator marked interrupted run failed after confirming process stopped"
        )
    elif args.command == "check-source":
        import re

        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", args.pipeline):
            parser.error("Invalid pipeline identifier")
        rules = load_rules(args.rules)
        engine = sqlserver_reader(settings.source_url.get_secret_value())
        run_id = store.start(args.pipeline, "external-read-only-validation")
        try:
            results = [QualityEngine(engine).check(r, store.baseline(args.pipeline, r.id)) for r in rules]
            store.finish(run_id, results)
        finally:
            engine.dispose()
        print(json.dumps(store.run(run_id)))


if __name__ == "__main__":
    main()
