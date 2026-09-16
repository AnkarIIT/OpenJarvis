from jarvis.agent.snapshots import SnapshotStore


def test_snapshot_restores_existing_file(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("before", encoding="utf-8")
    store = SnapshotStore(tmp_path / "snapshots")

    snapshot_id = store.snapshot_file(target, "task-1")
    target.write_text("after", encoding="utf-8")
    store.restore(snapshot_id)

    assert target.read_text(encoding="utf-8") == "before"


def test_snapshot_removes_new_file_on_restore(tmp_path):
    target = tmp_path / "new.txt"
    store = SnapshotStore(tmp_path / "snapshots")

    snapshot_id = store.snapshot_file(target, "task-1")
    target.write_text("created", encoding="utf-8")
    store.restore(snapshot_id)

    assert not target.exists()
