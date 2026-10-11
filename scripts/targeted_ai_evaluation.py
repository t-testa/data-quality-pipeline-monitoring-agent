"""Separate owner-approved three-attempt synthetic retest; offline mode is the default.

The original 12-attempt approval remains exhausted. Do not delete either ledger.
No command-line override may increase this approval's attempts, cost or request size.
"""

import argparse
import json
import logging
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import SecretStr

from scripts import live_ai_evaluation as base

ROOT = base.ROOT
LEDGER = ROOT / ".local" / "approved-targeted-ai-2026-10-11" / "attempts.sqlite"
REPORT = ROOT / "artifacts" / "targeted-ai-evaluation.json"
INDICES = (5, 6, 0)
CASES = tuple(base.CASES[i][0] for i in INDICES)
MAX_CALLS = 3
CAP = Decimal("0.01")
MAX_REQUEST_BYTES = 3000
# UTF-8 request bytes conservatively bound text tokens; reserve 2,000 more for
# protocol/schema framing. This local estimate is not a provider-side billing cap.
INPUT_ALLOWANCE = 5000
PER_CALL = INPUT_ALLOWANCE * base.INPUT_RATE + base.OUTPUT_LIMIT * base.OUTPUT_RATE


def reserved_cost(rows):
    return sum(
        (
            max(PER_CALL, Decimal(row["result"]["estimated_cost_usd"]))
            if row["result"] and row["result"].get("estimated_cost_usd") is not None
            else PER_CALL
            for row in rows
        ),
        Decimal(0),
    )


def reserve(case_id, path=LEDGER):
    if case_id not in CASES:
        raise ValueError("Unapproved targeted evaluation case")
    with base.ledger(path) as db:
        db.execute("BEGIN IMMEDIATE")
        rows = [
            {"result": json.loads(row[0]) if row[0] else None}
            for row in db.execute("SELECT result FROM attempts")
        ]
        if len(rows) >= MAX_CALLS or reserved_cost(rows) + PER_CALL > CAP:
            raise ValueError("Targeted attempt or budget limit reached")
        db.execute("INSERT INTO attempts VALUES(?,?,NULL)", (case_id, datetime.now(UTC).isoformat()))
        db.commit()


def case_run(index, key, live=False, path=LEDGER):
    if index not in INDICES:
        raise ValueError("Unapproved targeted evaluation case")
    return base.case_run(index, key, live, path, max_request_bytes=MAX_REQUEST_BYTES, reserve_attempt=reserve)


def summarize(path=LEDGER):
    rows = base.entries(path)
    return {
        "model_requested": base.MODEL,
        "approved_call_limit": MAX_CALLS,
        "attempts": len(rows),
        "approved_budget_usd": str(CAP),
        "full_evaluation_max_estimate_usd": str(MAX_CALLS * PER_CALL),
        "reserved_cost_upper_estimate_usd": str(reserved_cost(rows)),
        "actual_usage_estimated_cost_usd": str(
            sum(
                (
                    Decimal(r["result"]["estimated_cost_usd"])
                    for r in rows
                    if r["result"] and r["result"].get("estimated_cost_usd") is not None
                ),
                Decimal(0),
            )
        ),
        "unknown_usage_attempts": sum(not r["result"] or r["result"].get("usage") is None for r in rows),
        "cases": rows,
        "case_outcomes": [
            {
                "case": name,
                "status": next(
                    (r["result"]["status"] if r["result"] else "FAIL" for r in rows if r["case"] == name),
                    "NOT TESTED",
                ),
            }
            for name in CASES
        ],
        "not_a_provider_billing_cap": True,
    }


def preflight():
    key = base.approved_configuration()
    present = bool(key.get_secret_value().strip())
    # Exercise the exact adapter/schema with MockTransport and a placeholder key.
    offline = [case_run(i, SecretStr("offline-placeholder")) for i in INDICES]
    prior = base.entries(LEDGER)
    checks = {
        "key_configured": present,
        "model": base.MODEL,
        "worst_case_usd": str(MAX_CALLS * PER_CALL),
        "within_budget": MAX_CALLS * PER_CALL <= CAP,
        "input_token_allowance": INPUT_ALLOWANCE,
        "max_request_bytes": MAX_REQUEST_BYTES,
        "output_token_limit": base.OUTPUT_LIMIT,
        "sdk_timeout_seconds": 20,
        "worker_deadline_seconds": base.WALL_SECONDS,
        "automatic_retries": 0,
        "prior_attempts": len(prior),
        "offline_cases": [{k: r[k] for k in ("case", "status", "request_bytes")} for r in offline],
    }
    print(json.dumps(checks), flush=True)
    return present and checks["within_budget"] and all(r["status"] == "PASS" for r in offline)


def run_live():
    if not preflight():
        return 2
    for index in INDICES:
        name = base.CASES[index][0]
        prior = base.entries(LEDGER)
        if name in {r["case"] for r in prior}:
            continue  # A failed or ambiguous attempt is never retried.
        if len(prior) >= MAX_CALLS or reserved_cost(prior) + PER_CALL > CAP:
            print("STOP: targeted attempt or budget limit reached.", flush=True)
            break
        try:
            subprocess.run(
                [sys.executable, "-m", "scripts.targeted_ai_evaluation", "--worker", str(index)],
                cwd=ROOT,
                timeout=base.WALL_SECONDS,
                capture_output=True,
                check=True,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            row = next((r for r in base.entries(LEDGER) if r["case"] == name), None)
            if row and not row["result"]:
                base.record(
                    name,
                    {
                        "status": "FAIL",
                        "failure_type": "worker_timeout_or_exit",
                        "usage": None,
                        "estimated_cost_usd": None,
                    },
                    LEDGER,
                )
            print("STOP: worker failure; no retry.", flush=True)
            break
        row = next((r for r in base.entries(LEDGER) if r["case"] == name), None)
        if not row or not row["result"]:
            print("STOP: incomplete attempt; no retry.", flush=True)
            break
        result = row["result"]
        print(
            json.dumps(
                {k: result.get(k) for k in ("case", "status", "usage", "estimated_cost_usd", "failure_type")}
            ),
            flush=True,
        )
        if (
            result.get("http_status") in {401, 403, 429}
            or result.get("usage") is None
            or result["usage"]["input_tokens"] > INPUT_ALLOWANCE
            or Decimal(result["estimated_cost_usd"]) > PER_CALL
        ):
            print("STOP: provider/usage/budget guard; no further calls.", flush=True)
            break
    summary = summarize()
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return int(any(row["status"] != "PASS" for row in summary["case_outcomes"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--live", action="store_true")
    group.add_argument("--worker", type=int, choices=INDICES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    if args.worker is not None:
        key = base.approved_configuration()
        if not key.get_secret_value().strip():
            return 2
        result = case_run(args.worker, key, live=True)
        return 0 if result["request_count"] else 2
    if args.live:
        return run_live()
    return 0 if preflight() else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        print("STOP: targeted evaluation setup failed; no private exception details displayed.")
        raise SystemExit(2) from None
