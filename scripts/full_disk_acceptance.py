"""Destructive only inside an explicitly selected, empty 2 MiB /data tmpfs."""

import argparse
import errno
import json
import os
import sqlite3
from pathlib import Path

from dqagent.store import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--isolated-tmpfs", action="store_true", required=True)
    parser.parse_args()
    root = Path("/data")
    mounts = Path("/proc/mounts").read_text().splitlines()
    if not any(line.split()[1:3] == ["/data", "tmpfs"] for line in mounts):
        raise RuntimeError("Requires a disposable /data tmpfs, never a volume or host directory")
    size = os.statvfs(root)
    if size.f_blocks * size.f_frsize != 2097152 or any(root.iterdir()):
        raise RuntimeError("Requires a new empty 2 MiB tmpfs")
    store = Store(root)
    run = store.start("storage-full", "isolated-fault-test")
    filler = root / "synthetic-fill.bin"
    try:
        with filler.open("wb") as file:
            while True:
                file.write(b"x" * 4096)
    except OSError as exc:
        assert exc.errno == errno.ENOSPC
    failure = None
    try:
        store.finish(run, [])
    except sqlite3.Error as exc:
        failure = exc.sqlite_errorname
    assert failure is not None, "Full filesystem unexpectedly accepted a write"
    filler.unlink()
    assert store.run(run)["status"] == "running"
    assert store.results(run) == []
    store.finish(run, [], error="Operator confirmed failed writer stopped")
    with store.db() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    print(
        json.dumps(
            {
                "isolated_tmpfs_bytes": 2097152,
                "write_error": failure,
                "no_false_success": True,
                "operator_recovery": "PASS",
                "integrity": "ok",
                "existing_volume_mounted": False,
            }
        )
    )


if __name__ == "__main__":
    main()
