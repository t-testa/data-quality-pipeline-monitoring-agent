"""Exclusive, verified SQLite backup. Never overwrites an existing destination."""

import argparse
import os
import sqlite3
from pathlib import Path

from dqagent.settings import Settings


def backup(source_path: Path, destination: Path):
    if not source_path.is_file():
        raise ValueError("No monitoring database")
    # Atomic creation avoids a check-then-open overwrite race; POSIX permissions
    # are private from creation. Windows operators must also secure directory ACLs.
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    try:
        source = sqlite3.connect(f"file:{source_path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup integrity verification failed")
            finally:
                target.close()
        finally:
            source.close()
    except BaseException:
        destination.unlink(missing_ok=True)  # Only this newly created partial backup.
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    backup(Settings().data_dir / "monitoring.sqlite", args.destination)
    print("Verified monitoring backup created; protect it as private evidence.")


if __name__ == "__main__":
    main()
