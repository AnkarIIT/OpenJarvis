from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class AgentTask:
    task_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "pending"
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None

    def start(self) -> None:
        self.status = "running"
        self.started_at = datetime.now(timezone.utc).isoformat()

    def finish(self, status: str = "completed", error: str | None = None) -> None:
        self.status = status
        self.error = error
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }
