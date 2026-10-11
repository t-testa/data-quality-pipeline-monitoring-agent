"""Exact citation contracts and bounded, non-content-bearing failure observability."""

import json
import logging
import re
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from openai import APITimeoutError
from pydantic import SecretStr, ValidationError

from dqagent.contracts import Question
from dqagent.demo import scenario_demo
from dqagent.diagnostics import (
    Selection,
    SelectionRejected,
    ask_model,
    diagnose,
    reference_summary,
    validate_selection,
)


def enable_fake(settings):
    settings.openai_api_key = SecretStr("SYNTHETIC-KEY-NOT-FOR-LOGGING")
    settings.openai_model = "offline-placeholder"


def question(run, use_ai=True):
    return Question(
        pipeline=run["pipeline"], run_id=run["id"], question="SYNTHETIC PRIVATE QUESTION", use_ai=use_ai
    )


def test_healthy_projection_has_one_exact_citable_summary(store, settings, caplog):
    run = scenario_demo(store, "success")
    enable_fake(settings)
    baseline = diagnose(store, settings, question(run, False))

    def provider(_, prompt, context):
        assert context["allowed_guidance"] == []
        assert len(context["facts"]) == 1
        summary = context["facts"][0]
        assert summary["evidence_id"] == run["id"]
        assert re.fullmatch(r"[a-f0-9]{32}", summary["evidence_id"])
        assert summary["check_status_counts"] == {"pass": 10, "warning": 0, "failure": 0, "error": 0}
        return {"evidence_ids": [summary["evidence_id"]], "guidance": []}

    with caplog.at_level(logging.WARNING, logger="dqagent"):
        result = diagnose(store, settings, question(run), provider)
    assert result["ai_status"].startswith("available")
    assert result["ai_failure"] is None
    assert result["focus_evidence_ids"] == [run["id"]]
    assert result["facts"] == baseline["facts"]
    assert result["possible_explanations"] == []
    assert not [r for r in caplog.records if "ai_diagnostic_rejected" in r.message]


@pytest.mark.parametrize(
    "kind,reason,state",
    [
        ("empty", "empty_evidence_ids", "empty"),
        ("missing", "missing_evidence_ids", "missing"),
        ("null", "invalid_selection_schema", "invalid_type"),
        ("nonexistent", "unknown_evidence_reference", "list"),
        ("wrong-case", "unknown_evidence_reference", "list"),
        ("whitespace", "unknown_evidence_reference", "list"),
        ("check-name", "unknown_evidence_reference", "list"),
        ("passing-check", "unknown_evidence_reference", "list"),
        ("other-run", "unknown_evidence_reference", "list"),
        ("non-string", "invalid_selection_schema", "list"),
    ],
)
def test_rejected_references_preserve_facts_and_record_only_safe_metadata(
    kind, reason, state, store, settings, caplog
):
    run = scenario_demo(store, "success")
    other = scenario_demo(store, "duplicates")
    enable_fake(settings)
    baseline = diagnose(store, settings, question(run, False))
    options = {
        "empty": [],
        "null": None,
        "nonexistent": ["f" * 32],
        "wrong-case": [run["id"].upper()],
        "whitespace": [" " + run["id"]],
        "check-name": ["customer_key"],
        "passing-check": [store.results(run["id"])[0]["evidence_id"]],
        "other-run": [other["id"]],
        "non-string": [{"private": "SYNTHETIC ROW CONTENT"}],
    }
    raw = {"guidance": []}
    if kind != "missing":
        raw["evidence_ids"] = options[kind]
    with caplog.at_level(logging.WARNING, logger="dqagent"):
        result = diagnose(store, settings, question(run), lambda *_: raw)
    assert result["facts"] == baseline["facts"]
    assert result["focus_evidence_ids"] == result["possible_explanations"] == []
    assert result["ai_status"] == "unavailable: provider or grounding validation failed"
    failure = result["ai_failure"]
    assert failure["reason"] == reason
    assert failure["references"]["state"] == state
    events = [json.loads(r.message) for r in caplog.records if r.name == "dqagent"]
    assert len(events) == 1
    assert events[0] == {"event": "ai_diagnostic_rejected", "run_id": run["id"], **failure}
    serialized = json.dumps(events)
    assert other["id"] not in serialized
    for sensitive in ("SYNTHETIC ROW CONTENT", "SYNTHETIC PRIVATE QUESTION", "SYNTHETIC-KEY-NOT-FOR-LOGGING"):
        assert sensitive not in serialized


def test_unknown_reference_summary_cannot_disclose_even_secret_shaped_ids():
    secret = "SYNTHETIC PRIVATE TEXT password=not-a-real-password\n" * 1000
    values = [secret, "f" * 32, {"raw": secret}] * 10
    summary = reference_summary(values)
    assert summary["count"] == 30 and summary["omitted"] == 18
    assert len(summary["items"]) == 12
    assert len(json.dumps(summary)) < 2500
    assert "SYNTHETIC" not in json.dumps(summary)
    assert "f" * 32 not in json.dumps(summary)
    assert summary["items"][0]["characters"] == 256
    assert summary["items"][0]["truncated"]
    assert summary["items"][0]["fingerprint"] == reference_summary([secret])["items"][0]["fingerprint"]
    assert reference_summary(["a" * 32])["items"][0]["fingerprint"] != summary["items"][1]["fingerprint"]
    assert summary["items"][2]["kind"] == "non_string"
    assert SelectionRejected(secret).diagnostic["reason"] == "provider_error"


@pytest.mark.parametrize(
    "kind,reason",
    [("wrong-guidance", "guidance_not_allowed"), ("wrong-support", "guidance_reference_mismatch")],
)
def test_guidance_grounding_not_weakened(kind, reason, store, settings):
    run = scenario_demo(store, "duplicates")
    enable_fake(settings)
    check = next(c for c in store.results(run["id"]) if c["check_id"] == "customer_key")
    raw = {
        "evidence_ids": [check["evidence_id"] if kind == "wrong-guidance" else run["id"]],
        "guidance": ["schema" if kind == "wrong-guidance" else "duplicate"],
    }
    result = diagnose(store, settings, question(run), lambda *_: raw)
    assert result["ai_failure"]["reason"] == reason
    assert result["ai_failure"]["references"]["items"][0]["kind"] == "supplied"
    assert result["focus_evidence_ids"] == []
    assert result["possible_explanations"][0]["category"] == "duplicate"


@pytest.mark.parametrize("scenario", ["empty", "pipeline_failure"])
def test_missing_validation_still_accepts_run_summary_and_acknowledges_gap(scenario, store, settings):
    if scenario == "empty":
        rid = store.start("synthetic-empty", "test")
        store.finish(rid, [])
        run = store.run(rid)
    else:
        run = scenario_demo(store, scenario)
    enable_fake(settings)
    raw = {"evidence_ids": [run["id"]], "guidance": ["pipeline"] if run["error"] else []}
    result = diagnose(store, settings, question(run), lambda *_: raw)
    assert result["ai_failure"] is None
    assert result["ai_status"].startswith("available")
    assert result["facts"][0]["validation_status"] == "not_recorded"
    assert result["missing_evidence"]


@pytest.mark.parametrize(
    "raw,reason",
    [
        ({"evidence_ids": [], "guidance": []}, "empty_evidence_ids"),
        ({"guidance": []}, "missing_evidence_ids"),
        ({"evidence_ids": None, "guidance": []}, "invalid_selection_schema"),
        ({"evidence_ids": ["a" * 32] * 13, "guidance": []}, "invalid_selection_schema"),
        (
            {"evidence_ids": ["a" * 32], "guidance": ["SYNTHETIC PRIVATE CATEGORY"]},
            "invalid_selection_schema",
        ),
    ],
)
def test_sdk_validation_errors_are_classified_without_exposing_input(raw, reason, settings, monkeypatch):
    fake = MagicMock()
    try:
        Selection.model_validate(raw)
    except ValidationError as error:
        fake.return_value.__enter__.return_value.responses.parse.side_effect = error
    monkeypatch.setattr("openai.OpenAI", fake)
    with pytest.raises(SelectionRejected) as rejected:
        ask_model(settings, "private question", {"facts": [{"evidence_id": "a" * 32}]})
    assert rejected.value.diagnostic["reason"] == reason
    assert "SYNTHETIC PRIVATE CATEGORY" not in json.dumps(rejected.value.diagnostic)


def test_sdk_timeout_and_no_selection_have_explicit_reasons(settings, monkeypatch):
    fake = MagicMock()
    parse = fake.return_value.__enter__.return_value.responses.parse
    monkeypatch.setattr("openai.OpenAI", fake)
    parse.side_effect = APITimeoutError(request=httpx.Request("POST", "https://api.openai.com/v1/responses"))
    with pytest.raises(SelectionRejected) as caught:
        ask_model(settings, "why", {})
    assert caught.value.diagnostic["reason"] == "provider_timeout"
    assert caught.value.diagnostic["references"]["count"] is None
    parse.side_effect = None
    parse.return_value = SimpleNamespace(output_parsed=None)
    with pytest.raises(SelectionRejected) as caught:
        ask_model(settings, "why", {})
    assert caught.value.diagnostic["reason"] == "no_structured_selection"


@pytest.mark.parametrize(
    "exception,reason", [(TimeoutError, "provider_timeout"), (RuntimeError, "provider_error")]
)
def test_provider_failure_is_distinct_from_reference_failure(exception, reason, store, settings, caplog):
    run = scenario_demo(store, "success")
    enable_fake(settings)

    def fail(*_):
        raise exception("SYNTHETIC PRIVATE PROVIDER ERROR")

    with caplog.at_level(logging.WARNING, logger="dqagent"):
        result = diagnose(store, settings, question(run), fail)
    assert result["ai_failure"]["reason"] == reason
    assert result["ai_failure"]["references"] == {"state": "unavailable", "count": None, "items": []}
    assert "SYNTHETIC PRIVATE" not in caplog.text


def test_schema_prompt_and_mutated_instances_share_nonempty_contract(settings, monkeypatch):
    fake = MagicMock()
    fake.return_value.__enter__.return_value.responses.parse.return_value.output_parsed = Selection(
        evidence_ids=["a" * 32], guidance=[]
    )
    monkeypatch.setattr("openai.OpenAI", fake)
    choice = ask_model(settings, "why", {"facts": [{"evidence_id": "a" * 32}]})
    kwargs = fake.return_value.__enter__.return_value.responses.parse.call_args.kwargs
    assert kwargs["text_format"].model_json_schema()["properties"]["evidence_ids"]["minItems"] == 1
    instruction = kwargs["input"][0]["content"]
    for fragment in ("Copy evidence_id values exactly", "at least one", "healthy run", "empty guidance"):
        assert fragment in instruction
    choice.evidence_ids = []
    with pytest.raises(SelectionRejected) as caught:
        validate_selection(choice, ("a" * 32,))
    assert caught.value.diagnostic["reason"] == "empty_evidence_ids"


def test_unexpected_validation_defect_not_mislabeled_provider_failure(store, settings, monkeypatch):
    run = scenario_demo(store, "success")
    enable_fake(settings)

    def broken_validator(*_):
        raise RuntimeError("SYNTHETIC PRIVATE LOCAL ERROR")

    monkeypatch.setattr("dqagent.diagnostics.validate_selection", broken_validator)
    result = diagnose(
        store, settings, question(run), lambda *_: {"evidence_ids": [run["id"]], "guidance": []}
    )
    assert result["ai_failure"]["reason"] == "validation_error"
    assert "SYNTHETIC PRIVATE" not in json.dumps(result)


def test_adapter_schema_exception_retains_empty_reference_reason(store, settings):
    run = scenario_demo(store, "success")
    enable_fake(settings)

    def invalid_adapter(*_):
        return Selection(evidence_ids=[], guidance=[])

    result = diagnose(store, settings, question(run), invalid_adapter)
    assert result["ai_failure"]["reason"] == "empty_evidence_ids"
    assert result["ai_failure"]["references"]["count"] == 0
