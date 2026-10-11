"""Consistent local metadata backup using SQLite's online backup API."""

import argparse
import sqlite3
from pathlib import Path

from dqagent.settings import Settings

parser = argparse.ArgumentParser()
parser.add_argument("destination", type=Path)
args = parser.parse_args()
if args.destination.exists():
    parser.error("Backup destination already exists")
source_path = Settings().data_dir / "monitoring.sqlite"
if not source_path.exists():
    parser.error("No monitoring database")
source = sqlite3.connect(f"file:{source_path.resolve().as_posix()}?mode=ro", uri=True)
target = sqlite3.connect(args.destination)
try:
    source.backup(target)
    assert target.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
finally:
    source.close()
    target.close()
print("Verified monitoring backup created; protect it as private evidence.")
