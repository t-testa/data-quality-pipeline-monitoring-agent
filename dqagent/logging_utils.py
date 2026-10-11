import logging
import re


def redact_text(message, values=()):
    for value in values:
        if value:
            message = message.replace(value, "[REDACTED]")
    message = re.sub(r"(?i)(Bearer\s+)\S+", r"\1[REDACTED]", message)
    message = re.sub(r"(?i)((?:password|pwd|api_key|token)\s*[=:]\s*)[^;\s&]+", r"\1[REDACTED]", message)
    message = re.sub(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{16,}", "[REDACTED]", message)
    return message


class RedactSecrets(logging.Filter):
    def __init__(self, values=()):
        super().__init__()
        self.values = [value for value in values if value]

    def filter(self, record):
        record.msg, record.args = redact_text(record.getMessage(), self.values), ()
        # Tracebacks can include SQL/provider values that bypass formatted-message redaction.
        if record.exc_info:
            record.exc_info = None
            record.exc_text = None
        return True


def install_redaction(settings):
    secrets = [
        settings.api_token.get_secret_value(),
        settings.diagnostic_token.get_secret_value(),
        settings.source_url.get_secret_value(),
        settings.openai_api_key.get_secret_value(),
    ]
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "dqagent"):
        logger = logging.getLogger(name)
        for existing in list(logger.filters):
            if isinstance(existing, RedactSecrets):
                logger.removeFilter(existing)
        logger.addFilter(RedactSecrets(secrets))
    # SDK debug logs can include request bodies. Parent logger filters do not
    # protect propagated child records; disable these transport logs entirely.
    for name in ("openai", "httpx", "httpcore"):
        logger = logging.getLogger(name)
        logger.handlers = [logging.NullHandler()]
        logger.propagate = False
    logger = logging.getLogger("dqagent")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
