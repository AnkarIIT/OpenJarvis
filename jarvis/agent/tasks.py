from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class AgentTask:
    task_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "pending"
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    steps: list[dict[str, Any]] = field(default_factory=list)

    def start(self) -> None:
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()

    def finish(self, status: str = "completed", error: str | None = None) -> None:
        self.status = status
        self.error = error
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def add_step(self, phase: str, detail: str, status: str = "completed") -> None:
        self.steps.append({"phase": phase, "detail": detail, "status": status})

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "steps": self.steps,
        }


class TaskStore:
    def __init__(self, path: Path):
        self.path = path

    def save(self, task: AgentTask) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(task.as_dict(), ensure_ascii=True) + "\n")

    def latest(self) -> AgentTask | None:
        if not self.path.exists():
            return None
        lines = [line for line in self.path.read_text(encoding="utf-8").splitlines() if line]
        if not lines:
            return None
        data = json.loads(lines[-1])
        return AgentTask(
            task_id=data["task_id"],
            status=data["status"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            error=data.get("error"),
            steps=data.get("steps", []),
        )
