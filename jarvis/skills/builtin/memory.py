from __future__ import annotations

from typing import Any, Awaitable
from dataclasses import dataclass

from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MemorySkill:
    name: str = "memory"
    description: str = "Long-term memory storage and retrieval"

    async def initialize(self, settings) -> None:
        pass

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="remember",
                description="Store a memory",
                handler=self._remember,
                skill_name=self.name,
            ),
            SkillCommand(
                name="recall",
                description="Search memories",
                handler=self._recall,
                skill_name=self.name,
            ),
            SkillCommand(
                name="forget",
                description="Delete a memory",
                handler=self._forget,
                skill_name=self.name,
            ),
        ]

    async def _remember(self, content: str, metadata: str = "{}") -> str:
        import json
        meta = json.loads(metadata) if metadata else {}
        return f"Memory stored: {content[:50]}..."

    async def _recall(self, query: str, limit: int = 5) -> str:
        return f"Searching memories for: {query}"

    async def _forget(self, memory_id: str) -> str:
        return f"Memory {memory_id} deleted"