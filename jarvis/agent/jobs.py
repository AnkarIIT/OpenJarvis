from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable
from uuid import uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AgentJob:
    prompt: str
    run_at: str | None = None
    max_attempts: int = 1
    job_id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "pending"
    attempts: int = 0
    last_error: str | None = None
    completed_at: str | None = None

    def due(self, now: datetime | None = None) -> bool:
        if self.status != "pending":
            return False
        if not self.run_at:
            return True
        scheduled = datetime.fromisoformat(self.run_at.replace("Z", "+00:00"))
        return scheduled <= (now or _now())

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "prompt": self.prompt,
            "run_at": self.run_at,
            "max_attempts": self.max_attempts,
            "status": self.status,
            "attempts": self.attempts,
            "last_error": self.last_error,
            "completed_at": self.completed_at,
        }


class JobStore:
    def __init__(self, path: Path):
        self.path = path

    def _read(self) -> dict[str, AgentJob]:
        if not self.path.exists():
            return {}
        jobs: dict[str, AgentJob] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            data = json.loads(line)
            job = AgentJob(
                prompt=data["prompt"],
                run_at=data.get("run_at"),
                max_attempts=data.get("max_attempts", 1),
                job_id=data["job_id"],
                status=data.get("status", "pending"),
                attempts=data.get("attempts", 0),
                last_error=data.get("last_error"),
                completed_at=data.get("completed_at"),
            )
            jobs[job.job_id] = job
        return jobs

    def _append(self, job: AgentJob) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(job.as_dict(), ensure_ascii=True) + "\n")

    def save(self, job: AgentJob) -> None:
        self._append(job)

    def list(self) -> list[AgentJob]:
        return list(self._read().values())

    def get(self, job_id: str) -> AgentJob | None:
        return self._read().get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job or job.status not in {"pending", "failed"}:
            return False
        job.status = "cancelled"
        self._append(job)
        return True


class JobRunner:
    def __init__(self, store: JobStore, execute: Callable[[str], Awaitable[Any]]):
        self.store = store
        self.execute = execute

    async def run_due_once(self) -> AgentJob | None:
        job = next((candidate for candidate in self.store.list() if candidate.due()), None)
        if job is None:
            return None
        job.status = "running"
        job.attempts += 1
        self.store.save(job)
        try:
            await self.execute(job.prompt)
        except asyncio.CancelledError:
            job.status = "cancelled"
            self.store.save(job)
            raise
        except Exception as exc:
            job.last_error = str(exc)
            job.status = "failed" if job.attempts >= job.max_attempts else "pending"
            self.store.save(job)
            return job
        job.status = "completed"
        job.completed_at = _now().isoformat()
        self.store.save(job)
        return job
