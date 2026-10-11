import logging
import re


class RedactSecrets(logging.Filter):
    def __init__(self, values=()):
        super().__init__()
        self.values = [value for value in values if value]

    def filter(self, record):
        message = record.getMessage()
        for value in self.values:
            message = message.replace(value, "[REDACTED]")
        message = re.sub(r"(?i)(Bearer\s+)\S+", r"\1[REDACTED]", message)
        message = re.sub(r"(?i)((?:password|pwd|api_key|token)=)[^;\s&]+", r"\1[REDACTED]", message)
        record.msg, record.args = message, ()
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
