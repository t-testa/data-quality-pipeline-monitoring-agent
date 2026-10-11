"""Fail on accidentally tracked runtime files or recognizable credentials; print paths only."""

import re
import subprocess
from pathlib import Path

paths = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
bad = []
known_secrets = []
if Path(".env").exists():
    for line in Path(".env").read_text().splitlines():
        key, _, value = line.partition("=")
        if any(part in key for part in ("TOKEN", "KEY", "PASSWORD", "SOURCE_URL")) and len(value) >= 16:
            known_secrets.append(value)
patterns = [
    r"sk-(?:proj-)?[A-Za-z0-9_-]{30,}",
    r"gh[pousr]_[A-Za-z0-9]{30,}",
    r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----",
]
for path in filter(None, paths):
    file = Path(path)
    if path.startswith(("data/", ".local/", ".venv/")) or file.name == ".env":
        bad.append(path)
    if file.is_file() and file.stat().st_size < 2_000_000:
        content = file.read_text(encoding="utf-8", errors="ignore")
        if any(re.search(pattern, content) for pattern in patterns) or any(
            value in content for value in known_secrets
        ):
            bad.append(path)
if bad:
    raise SystemExit("Potential secret/runtime files: " + ", ".join(sorted(set(bad))))
print("Tracked-file secret check passed (heuristic; complements manual review).")
