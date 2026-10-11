"""Create CI-only random credentials without printing secrets."""

import secrets
from pathlib import Path

with Path(".env").open("x") as out:
    out.write(f"DQ_API_TOKEN={secrets.token_urlsafe(32)}\nDQ_DIAGNOSTIC_TOKEN={secrets.token_urlsafe(32)}\n")
