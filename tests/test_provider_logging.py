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
