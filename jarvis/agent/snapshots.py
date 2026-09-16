from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class SnapshotStore:
    def __init__(self, root: Path):
        self.root = root
        self.index = root / "index.jsonl"

    def snapshot_file(self, path: Path, task_id: str | None) -> str:
        snapshot_id = str(uuid4())
        self.root.mkdir(parents=True, exist_ok=True)
        backup = self.root / snapshot_id
        backup.mkdir(parents=True, exist_ok=True)
        existed = path.exists()
        if existed:
            if not path.is_file():
                raise ValueError(f"Snapshot only supports files: {path}")
            shutil.copy2(path, backup / "content")
        event = {
            "snapshot_id": snapshot_id,
            "path": str(path),
            "existed": existed,
            "task_id": task_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.index.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=True) + "\n")
        return snapshot_id

    def restore(self, snapshot_id: str) -> Path:
        if not self.index.exists():
            raise ValueError(f"Snapshot not found: {snapshot_id}")
        event = None
        for line in self.index.read_text(encoding="utf-8").splitlines():
            if line:
                candidate = json.loads(line)
                if candidate.get("snapshot_id") == snapshot_id:
                    event = candidate
        if event is None:
            raise ValueError(f"Snapshot not found: {snapshot_id}")
        path = Path(event["path"])
        backup = self.root / snapshot_id / "content"
        if event["existed"]:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, path)
        elif path.exists():
            path.unlink()
        return path
