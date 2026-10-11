"""No paid transport: enforce the separate three-attempt / one-cent approval."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from pydantic import SecretStr

from scripts import live_ai_evaluation as base
from scripts import targeted_ai_evaluation as targeted


@pytest.mark.parametrize("index", targeted.INDICES)
def test_targeted_protocol_and_required_findings(index):
    result = targeted.case_run(index, SecretStr("offline-placeholder"))
    assert result["status"] == "PASS", result["checks"]
    assert result["request_count"] == 1
    assert result["request_bytes"] <= targeted.MAX_REQUEST_BYTES
    assert result["investigation"]["ai_failure"] is None
    assert result["investigation"]["focus_evidence_ids"]
    assert result["model"] == "gpt-4.1-mini-2025-04-14"


def test_separate_approval_is_bounded_durable_and_cannot_retry(tmp_path):
    path = tmp_path / "targeted.sqlite"
    assert targeted.LEDGER != base.LEDGER
    assert targeted.PER_CALL * 3 == Decimal("0.00888") < targeted.CAP
    assert targeted.MAX_REQUEST_BYTES + 2000 == targeted.INPUT_ALLOWANCE
    targeted.reserve("healthy", path)
    with pytest.raises(sqlite3.IntegrityError):
        targeted.reserve("healthy", path)
    with pytest.raises(ValueError, match="Unapproved"):
        targeted.reserve("schema-drift", path)
    targeted.reserve("no-validation", path)
    targeted.reserve("duplicate", path)
    with pytest.raises(ValueError, match="limit"):
        targeted.reserve("healthy", path)
    summary = targeted.summarize(path)
    assert summary["attempts"] == summary["unknown_usage_attempts"] == 3
    assert all(r["status"] == "FAIL" for r in summary["case_outcomes"])


def test_concurrent_targeted_reservations_do_not_multiply_calls(tmp_path):
    path = tmp_path / "targeted.sqlite"

    def attempt(name):
        try:
            targeted.reserve(name, path)
            return True
        except (ValueError, sqlite3.IntegrityError):
            return False

    with ThreadPoolExecutor(max_workers=3) as pool:
        outcomes = list(pool.map(attempt, targeted.CASES * 3))
    assert sum(outcomes) == 3
    assert len(base.entries(path)) == 3


def test_cost_overrun_charges_actual_cost_before_next_attempt(tmp_path):
    path = tmp_path / "targeted.sqlite"
    targeted.reserve("healthy", path)
    base.record("healthy", {"status": "FAIL", "estimated_cost_usd": "0.008", "usage": {}}, path)
    with pytest.raises(ValueError, match="budget"):
        targeted.reserve("duplicate", path)
    assert len(base.entries(path)) == 1


def test_oversized_request_rejected_before_reservation_and_network(tmp_path, monkeypatch):
    monkeypatch.setattr(targeted, "MAX_REQUEST_BYTES", 1)
    path = tmp_path / "targeted.sqlite"
    result = targeted.case_run(5, SecretStr("offline-placeholder"), live=True, path=path)
    assert result["request_count"] == 0 and result["status"] == "FAIL"
    assert not path.exists()


def test_missing_key_blocks_workers(monkeypatch):
    monkeypatch.setattr(targeted, "preflight", lambda: False)
    monkeypatch.setattr(targeted.subprocess, "run", lambda *a, **kw: pytest.fail("Unexpected worker"))
    assert targeted.run_live() == 2


def test_worker_unknown_outcome_is_recorded_once_and_stops(tmp_path, monkeypatch):
    path = tmp_path / "targeted.sqlite"
    report = tmp_path / "report.json"
    monkeypatch.setattr(targeted, "LEDGER", path)
    monkeypatch.setattr(targeted, "REPORT", report)
    monkeypatch.setattr(targeted, "preflight", lambda: True)
    original_summary = targeted.summarize
    monkeypatch.setattr(targeted, "summarize", lambda: original_summary(path))
    calls = []

    def timeout(*args, **kwargs):
        calls.append(args)
        targeted.reserve("healthy", path)
        raise targeted.subprocess.TimeoutExpired("worker", 30)

    monkeypatch.setattr(targeted.subprocess, "run", timeout)
    assert targeted.run_live() == 1
    assert len(calls) == 1
    result = json.loads(report.read_text())
    assert result["attempts"] == result["unknown_usage_attempts"] == 1
    assert result["cases"][0]["result"]["failure_type"] == "worker_timeout_or_exit"


def test_completed_approval_never_launches_another_worker(tmp_path, monkeypatch):
    path = tmp_path / "targeted.sqlite"
    for name in targeted.CASES:
        targeted.reserve(name, path)
        base.record(name, {"status": "PASS", "usage": {}, "estimated_cost_usd": "0.0001"}, path)
    monkeypatch.setattr(targeted, "LEDGER", path)
    monkeypatch.setattr(targeted, "REPORT", tmp_path / "report.json")
    monkeypatch.setattr(targeted, "preflight", lambda: True)
    original_summary = targeted.summarize
    monkeypatch.setattr(targeted, "summarize", lambda: original_summary(path))
    monkeypatch.setattr(targeted.subprocess, "run", lambda *a, **kw: pytest.fail("Unexpected extra worker"))
    assert targeted.run_live() == 0
    assert len(base.entries(path)) == 3


def test_unapproved_case_never_reaches_adapter():
    with pytest.raises(ValueError, match="Unapproved"):
        targeted.case_run(1, SecretStr("offline-placeholder"))
