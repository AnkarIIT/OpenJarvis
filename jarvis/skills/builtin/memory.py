from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Awaitable

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class MemorySkill:
    name: str = "memory"
    description: str = "Long-term memory storage and retrieval via VectorStore"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings
        self._vector_store = None

    async def initialize(self, settings: Settings) -> None:
        self.settings = settings
        if settings.memory.enabled:
            try:
                from jarvis.memory.vector_store import VectorStore
                self._vector_store = VectorStore(settings)
                await self._vector_store.initialize()
            except Exception as e:
                logger.error(f"MemorySkill failed to initialize VectorStore: {e}")
                self._vector_store = None

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="remember",
                description="Store a memory in long-term vector storage",
                handler=self._remember,
                skill_name=self.name,
            ),
            SkillCommand(
                name="recall",
                description="Search long-term memories by semantic similarity",
                handler=self._recall,
                skill_name=self.name,
            ),
            SkillCommand(
                name="forget",
                description="Delete a memory by ID",
                handler=self._forget,
                skill_name=self.name,
            ),
        ]

    async def _remember(self, content: str, metadata: str = "{}") -> str:
        if not self._vector_store:
            return "Memory store not initialized. Enable memory in settings."

        try:
            meta = json.loads(metadata) if metadata else {}
        except json.JSONDecodeError:
            meta = {}

        try:
            memory_id = await self._vector_store.add_memory(content, meta)
            return f"Memory stored with ID: {memory_id}"
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            return f"Failed to store memory: {e}"

    async def _recall(self, query: str, limit: int = 5) -> str:
        if not self._vector_store:
            return "Memory store not initialized. Enable memory in settings."

        try:
            results = await self._vector_store.search(query, limit)
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return f"Memory search failed: {e}"

        if not results:
            return f"No memories found for: {query}"

        lines = [f"Found {len(results)} memories for '{query}':"]
        for r in results:
            score = r.get("score", 0)
            content = r.get("content", "")
            memory_id = r.get("id", "")
            lines.append(f"- [{memory_id}] (score: {score:.2f}) {content[:300]}")
        return "\n".join(lines)

    async def _forget(self, memory_id: str) -> str:
        if not self._vector_store:
            return "Memory store not initialized. Enable memory in settings."

        try:
            ok = await self._vector_store.delete_memory(memory_id)
            if ok:
                return f"Memory {memory_id} deleted."
            return f"Memory {memory_id} not found or could not be deleted."
        except Exception as e:
            logger.error(f"Failed to delete memory: {e}")
            return f"Failed to delete memory: {e}"
