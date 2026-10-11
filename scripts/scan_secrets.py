"""Fail on accidentally tracked runtime files or recognizable credentials; print paths only."""

import argparse
import re
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--history", action="store_true")
args = parser.parse_args()
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
if args.history:
    objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"]).decode().splitlines()
    for entry in objects:
        oid, _, path = entry.partition(" ")
        if subprocess.check_output(["git", "cat-file", "-t", oid]).strip() != b"blob":
            continue
        if path.startswith(("data/", ".local/", ".venv/", "artifacts/")) or Path(path).name == ".env":
            bad.append("history:" + path)
        content = subprocess.check_output(["git", "cat-file", "blob", oid]).decode("utf-8", errors="ignore")
        if any(re.search(pattern, content) for pattern in patterns) or any(
            value in content for value in known_secrets
        ):
            bad.append("history:" + path)
if bad:
    raise SystemExit("Potential secret/runtime files: " + ", ".join(sorted(set(bad))))
print(
    "Tracked-file"
    + (" and full reachable history" if args.history else "")
    + " secret check passed (heuristic; complements manual review)."
)
