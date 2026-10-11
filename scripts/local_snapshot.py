"""Stopped-volume backup and restore-to-new-volume; no service stop, overwrite or deletion.

Archive creation/restoration runs inside a network-disabled, unprivileged helper.
Keep all writers stopped for the entire backup operation, including host writers.
Only restore your own trusted backups; a checksum detects corruption, not forgery.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tarfile
from contextlib import closing
from pathlib import Path, PurePosixPath


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def members_checked(archive):
    members = archive.getmembers()
    names = set()
    for item in members:
        name = PurePosixPath(item.name)
        if (
            not item.isfile()
            or name.is_absolute()
            or ".." in name.parts
            or "\\" in item.name
            or ":" in item.name
            or str(name) != item.name
            or item.name in names
        ):
            raise ValueError("Unsafe or duplicate archive member")
        names.add(item.name)
    if "monitoring.sqlite" not in names:
        raise ValueError("Archive has no monitoring database")
    return members


def check_databases(root):
    databases = list(root.rglob("*.sqlite"))
    if not (root / "monitoring.sqlite").is_file():
        raise ValueError("No monitoring database")
    for path in databases:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Database integrity failure")
    return len(databases)


def create_archive(source, destination):
    if destination.exists() or Path(str(destination) + ".sha256").exists():
        raise ValueError("Backup destination already exists")
    files = sorted(source.rglob("*"))
    if any(p.is_symlink() or (not p.is_file() and not p.is_dir()) for p in files):
        raise ValueError("Source contains unsupported links or special files")
    if not (source / "monitoring.sqlite").is_file():
        raise ValueError("No monitoring database")
    # Stopped-volume copy includes all SQLite/WAL files and loader checkpoints.
    # Do not open source SQLite here: even read-only WAL access can create shm files.
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output, tarfile.open(fileobj=output, mode="w:gz") as archive:
        for path in files:
            if path.is_file():
                archive.add(path, arcname=path.relative_to(source).as_posix(), recursive=False)
    with Path(str(destination) + ".sha256").open("x", encoding="ascii") as output:
        output.write(digest(destination) + "\n")
    return {"archive_created": True, "files": sum(p.is_file() for p in files), "sha256": digest(destination)}


def restore_archive(source, target):
    if not target.is_dir() or any(target.iterdir()):
        raise ValueError("Restore requires an empty destination")
    expected = Path(str(source) + ".sha256").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[a-f0-9]{64}", expected) or digest(source) != expected:
        raise ValueError("Backup checksum mismatch")
    with tarfile.open(source, "r:gz") as archive:
        members = members_checked(archive)
        if sum(item.size for item in members) + 64 * 1024 * 1024 > shutil.disk_usage(target).free:
            raise ValueError("Insufficient restore space")
        for item in members:
            destination = target / item.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Never extract links, metadata, permissions or overwrite an existing file.
            with archive.extractfile(item) as incoming, destination.open("xb") as outgoing:
                shutil.copyfileobj(incoming, outgoing)
    count = check_databases(target)
    return {"restored": True, "databases_integrity_ok": count, "sha256": expected}


def docker(*args):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError("Docker operation failed; inspect local Docker status")
    return result.stdout.strip()


def operate(action, volume, archive, image):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{1,120}", volume):
        raise ValueError("Invalid Docker volume name")
    archive = archive.resolve()
    script = Path(__file__).resolve()
    if any("," in str(p) for p in (archive, script)):
        raise ValueError("Docker bind paths cannot contain commas")
    docker("image", "inspect", image, "--format", "{{.Id}}")  # Never pull implicitly.
    volumes = docker("volume", "ls", "--format", "{{.Name}}").splitlines()
    if action == "backup":
        if volume not in volumes:
            raise ValueError("Source volume does not exist")
        if docker("ps", "-q", "--filter", "volume=" + volume):
            raise ValueError("Stop all containers using the source volume before backup")
        if archive.exists() or Path(str(archive) + ".sha256").exists():
            raise ValueError("Backup destination already exists")
        archive.parent.mkdir(parents=True, exist_ok=True)
    else:
        if volume in volumes:
            raise ValueError("Restore volume already exists; choose a new name")
        if not archive.is_file() or not Path(str(archive) + ".sha256").is_file():
            raise ValueError("Backup archive/checksum missing")
        # Validate before creating anything in Docker.
        if digest(archive) != Path(str(archive) + ".sha256").read_text(encoding="ascii").strip():
            raise ValueError("Backup checksum mismatch")
        with tarfile.open(archive, "r:gz") as saved:
            members_checked(saved)
        docker("volume", "create", "--label", "northwatch.restore=true", volume)
    mounts = [
        "--mount",
        f"type=volume,source={volume},target=/data" + (",readonly" if action == "backup" else ""),
        "--mount",
        f"type=bind,source={archive.parent},target=/backup" + (",readonly" if action == "restore" else ""),
        "--mount",
        f"type=bind,source={script},target=/ops/local_snapshot.py,readonly",
    ]
    output = docker(
        "run",
        "--rm",
        "--pull",
        "never",
        "--network",
        "none",
        "--read-only",
        "--user",
        "10001:10001",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--memory",
        "256m",
        "--pids-limit",
        "64",
        *mounts,
        "--entrypoint",
        "python",
        image,
        "/ops/local_snapshot.py",
        "--inside",
        action,
        "/data",
        "/backup/" + archive.name,
    )
    return json.loads(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("volume", help="Stopped source volume or NEW restore volume name")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--image", default="northwatch-local:candidate", help="Already built local image")
    args = parser.parse_args()
    if args.inside:
        operation = (
            create_archive if args.action == "backup" else lambda data, saved: restore_archive(saved, data)
        )
        result = operation(Path(args.volume), args.archive)
    else:
        result = operate(args.action, args.volume, args.archive, args.image)
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit(
            "Snapshot operation failed; no existing history was overwritten. Inspect paths, stopped-volume state and available space."
        ) from None
