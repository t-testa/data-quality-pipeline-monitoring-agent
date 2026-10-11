import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from dqagent.diagnostics import Selection, ask_model
from dqagent.logging_utils import RedactSecrets


def test_provider_structured_contract_and_refusal(settings, monkeypatch):
    client = MagicMock()
    fake = client.return_value.__enter__.return_value
    parsed = Selection(evidence_ids=["evidence"], guidance=["duplicate"])
    fake.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)
    monkeypatch.setattr("openai.OpenAI", client)
    assert ask_model(settings, "why", {"facts": []}) == parsed
    params = fake.responses.parse.call_args.kwargs
    assert params["store"] is False
    assert params["max_output_tokens"] == 600
    assert params["text_format"] is Selection
    fake.responses.parse.return_value = SimpleNamespace(output_parsed=None)
    with pytest.raises(ValueError):
        ask_model(settings, "why", {})


def test_log_redaction():
    record = logging.LogRecord(
        "dqagent", logging.ERROR, "", 0, "Bearer secret-value password=hunter2 custom-secret", (), None
    )
    assert RedactSecrets(["custom-secret"]).filter(record)
    assert "secret-value" not in record.getMessage()
    assert "hunter2" not in record.getMessage()
    assert "custom-secret" not in record.getMessage()


def test_failed_query_does_not_imply_bad_data(store, settings):
    from dqagent.contracts import Question, Result
    from dqagent.diagnostics import diagnose
    from dqagent.quality import utcnow

    run = store.start("unreachable-source", "test")
    store.finish(
        run,
        [
            Result(
                check_id="fresh",
                name="Freshness",
                table="x",
                kind="freshness",
                executed_at=utcnow(),
                status="error",
                measured=None,
                expected={},
                details={},
                duration_ms=1,
            )
        ],
    )
    response = diagnose(store, settings, Question(pipeline="unreachable-source", question="Is it stale?"))
    explanation = response["possible_explanations"][0]
    assert explanation["category"] == "check_error"
    assert "unknown" in explanation["text"]
