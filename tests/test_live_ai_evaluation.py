"""Offline regression checks for the separately authorized live-evaluation harness."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from pydantic import SecretStr

from scripts import live_ai_evaluation as evaluation


@pytest.mark.parametrize("index", range(evaluation.MAX_CALLS), ids=[c[0] for c in evaluation.CASES])
def test_protocol_fixtures_use_production_projection_and_grounding(index):
    result = evaluation.case_run(index, SecretStr("offline-placeholder"))
    assert result["mode"] == "offline-protocol-fixture"
    assert result["status"] == "PASS", result["checks"]
    assert result["request_count"] == 1
    assert result["request_bytes"] <= evaluation.MAX_REQUEST_BYTES
    assert result["request_method"] == "POST"
    assert result["request_url"] == "https://api.openai.com/v1/responses"
    assert result["model"] == evaluation.MODEL
    assert result["usage"] == {"input_tokens": 100, "output_tokens": 40, "total_tokens": 140}
    assert result["estimated_cost_usd"] == "0.0001040"


def test_budget_persisted_before_io_and_cannot_repeat(tmp_path):
    path = tmp_path / "ledger.sqlite"
    evaluation.reserve("duplicate", path)
    assert evaluation.entries(path)[0]["result"] is None
    with pytest.raises(sqlite3.IntegrityError):
        evaluation.reserve("duplicate", path)
    summary = evaluation.summarize(path)
    assert summary["attempts"] == 1
    assert summary["unknown_usage_attempts"] == 1
    assert Decimal(summary["reserved_cost_upper_estimate_usd"]) == evaluation.PER_CALL
    assert Decimal(summary["full_evaluation_max_estimate_usd"]) == Decimal("0.1075200")


def test_insufficient_budget_rejects_before_attempt(tmp_path):
    path = tmp_path / "ledger.sqlite"
    with pytest.raises(ValueError, match="budget"):
        evaluation.reserve("duplicate", path, cap=evaluation.PER_CALL - Decimal("0.000001"))
    assert evaluation.entries(path) == []


def test_parallel_reservation_cannot_exceed_approval(tmp_path):
    path = tmp_path / "ledger.sqlite"
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda case: evaluation.reserve(case[0], path), evaluation.CASES))
    assert len(evaluation.entries(path)) == 12
    with pytest.raises(ValueError, match="limit"):
        evaluation.reserve("duplicate", path)


def test_unknown_and_success_usage_remain_separate(tmp_path):
    path = tmp_path / "ledger.sqlite"
    evaluation.reserve("duplicate", path)
    evaluation.reserve("foreign-key", path)
    evaluation.record(
        "duplicate", {"status": "PASS", "usage": {"input_tokens": 100}, "estimated_cost_usd": "0.001"}, path
    )
    summary = evaluation.summarize(path)
    assert summary["unknown_usage_attempts"] == 1
    assert Decimal(summary["actual_usage_estimated_cost_usd"]) == Decimal("0.001")
    assert Decimal(summary["reserved_cost_upper_estimate_usd"]) == 2 * evaluation.PER_CALL


def test_missing_key_does_not_launch_worker(monkeypatch):
    monkeypatch.setattr(evaluation, "approved_configuration", lambda: SecretStr(""))
    monkeypatch.setattr(evaluation.subprocess, "run", lambda *a, **kw: pytest.fail("Unexpected worker"))
    assert evaluation.run_live() == 2


def test_model_change_rejected_before_network(settings, monkeypatch):
    settings.openai_model = "unapproved-model"
    monkeypatch.setattr(evaluation, "Settings", lambda: settings)
    with pytest.raises(ValueError, match="differs"):
        evaluation.approved_configuration()


def test_bad_model_output_fails_quality_while_facts_remain_safe(monkeypatch):
    original = evaluation.ask_model

    def bad_choice(*args):
        choice = original(*args)
        choice.evidence_ids = ["invented-id"]
        return choice

    monkeypatch.setattr(evaluation, "ask_model", bad_choice)
    result = evaluation.case_run(0, SecretStr("offline-placeholder"))
    assert result["status"] == "FAIL"
    assert result["checks"]["structured_and_grounded"] is False
    assert result["checks"]["facts_unchanged"] is True
    assert result["checks"]["root_causes_unconfirmed"] is True


@pytest.mark.parametrize("failure", ["timeout", "http-error", "invalid-contract"])
def test_provider_failures_have_one_attempt_and_no_raw_error(monkeypatch, failure):
    import httpx

    original_transport = httpx.MockTransport

    def transport(handler):
        def fail(request):
            if failure == "timeout":
                raise httpx.ReadTimeout("SYNTHETIC_PRIVATE_PROVIDER_MESSAGE")
            if failure == "http-error":
                return httpx.Response(500, json={"error": {"message": "SYNTHETIC_PRIVATE_PROVIDER_MESSAGE"}})
            response = handler(request)
            payload = response.json()
            payload["output"][0]["content"][0]["text"] = json.dumps(
                {"sql": "SYNTHETIC_PRIVATE_PROVIDER_MESSAGE"}
            )
            return httpx.Response(200, json=payload)

        return original_transport(fail)

    monkeypatch.setattr(httpx, "MockTransport", transport)
    result = evaluation.case_run(0, SecretStr("offline-placeholder"))
    assert result["request_count"] == 1
    assert result["status"] == "FAIL"
    assert result["checks"]["facts_unchanged"]
    assert "SYNTHETIC_PRIVATE_PROVIDER_MESSAGE" not in json.dumps(result)
    if failure == "invalid-contract":
        assert result["usage"]["total_tokens"] == 140
    else:
        assert result.get("usage") is None


def test_credential_in_body_blocked_before_transport(monkeypatch):
    original = evaluation.ask_model

    def poisoned_prompt(config, question, evidence):
        return original(config, question + " offline-placeholder", evidence)

    monkeypatch.setattr(evaluation, "ask_model", poisoned_prompt)
    result = evaluation.case_run(0, SecretStr("offline-placeholder"))
    assert result["request_count"] == 0
    assert result["status"] == "FAIL"
    assert result.get("usage") is None


def test_healthy_empty_selection_reproduces_safe_fallback_offline(monkeypatch):
    # Plausible explanation of the live healthy failure, not a replay of its raw
    # response: the initial evaluator did not retain rejected reference lists.
    original = evaluation.ask_model

    def empty_selection(*args):
        choice = original(*args)
        choice.evidence_ids = []
        choice.guidance = []
        return choice

    monkeypatch.setattr(evaluation, "ask_model", empty_selection)
    result = evaluation.case_run(5, SecretStr("offline-placeholder"))
    assert result["status"] == "FAIL"
    assert result["checks"]["facts_unchanged"]
    assert result["investigation"]["facts"][0]["status"] == "success"
    assert result["investigation"]["possible_explanations"] == []
    assert result["investigation"]["ai_status"] == "unavailable: provider or grounding validation failed"
