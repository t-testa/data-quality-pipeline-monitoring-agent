import hashlib
import io
import tarfile
from pathlib import Path

import pytest

from dqagent.demo import run_demo, scenario_demo
from dqagent.store import Store
from scripts.local_snapshot import create_archive, digest, operate, restore_archive


def test_full_snapshot_preserves_history_evidence_and_incremental_checkpoint(tmp_path):
    store = Store(tmp_path / "source")
    run = scenario_demo(store, "duplicates")
    expected_run, expected_checks = store.run(run["id"]), store.results(run["id"])
    archive = tmp_path / "saved.tar.gz"
    created = create_archive(store.path.parent, archive)
    restored = tmp_path / "restored"
    restored.mkdir()
    result = restore_archive(archive, restored)
    assert created["sha256"] == result["sha256"]
    assert result["databases_integrity_ok"] >= 2
    recovered = Store(restored)
    assert recovered.run(run["id"]) == expected_run
    assert recovered.results(run["id"]) == expected_checks
    replay = run_demo(recovered, "duplicates")
    assert replay["records_processed"] == 0
    assert (store.path.parent / "demo" / "duplicates.sqlite").is_file()


def test_no_overwrite_of_backup_or_restored_history(tmp_path):
    store = Store(tmp_path / "source")
    scenario_demo(store, "success")
    archive = tmp_path / "saved.tar.gz"
    create_archive(store.path.parent, archive)
    original = digest(archive)
    with pytest.raises(ValueError, match="already exists"):
        create_archive(store.path.parent, archive)
    assert digest(archive) == original
    restored = tmp_path / "restored"
    restored.mkdir()
    marker = restored / "keep"
    marker.write_text("existing data")
    with pytest.raises(ValueError, match="empty"):
        restore_archive(archive, restored)
    assert marker.read_text() == "existing data"


def test_corrupt_archive_rejected_before_any_write(tmp_path):
    store = Store(tmp_path / "source")
    archive = tmp_path / "saved.tar.gz"
    create_archive(store.path.parent, archive)
    archive.write_bytes(archive.read_bytes() + b"corrupt")
    restored = tmp_path / "restored"
    restored.mkdir()
    with pytest.raises(ValueError, match="checksum"):
        restore_archive(archive, restored)
    assert list(restored.iterdir()) == []


@pytest.mark.parametrize("kind", ["traversal", "absolute", "symlink", "hardlink", "duplicate"])
def test_unsafe_archive_members_rejected_before_writes(tmp_path, kind):
    archive = tmp_path / "malformed.tar.gz"
    with tarfile.open(archive, "w:gz") as output:
        info = tarfile.TarInfo("monitoring.sqlite")
        info.size = 1
        output.addfile(info, io.BytesIO(b"x"))
        info = tarfile.TarInfo(
            {"traversal": "../outside", "absolute": "/outside"}.get(kind, "monitoring.sqlite")
        )
        if kind in {"symlink", "hardlink"}:
            info.type = tarfile.SYMTYPE if kind == "symlink" else tarfile.LNKTYPE
            info.linkname = "/outside"
        output.addfile(info)
    Path(str(archive) + ".sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest())
    target = tmp_path / "restored"
    target.mkdir()
    with pytest.raises(ValueError, match="Unsafe"):
        restore_archive(archive, target)
    assert list(target.iterdir()) == []


def test_running_volume_refused_without_starting_helper(tmp_path, monkeypatch):
    calls = []

    def fake(*args):
        calls.append(args)
        return {"image": "sha256:synthetic", "volume": "history", "ps": "active-container"}[args[0]]

    monkeypatch.setattr("scripts.local_snapshot.docker", fake)
    with pytest.raises(ValueError, match="Stop all"):
        operate("backup", "history", tmp_path / "saved.tar.gz", "local-image")
    assert not any(c[0] == "run" for c in calls)
    assert not (tmp_path / "saved.tar.gz").exists()


def test_restore_refuses_existing_volume_before_helper(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.local_snapshot.docker", lambda *args: "history")
    with pytest.raises(ValueError, match="already exists"):
        operate("restore", "history", tmp_path / "saved.tar.gz", "local-image")
