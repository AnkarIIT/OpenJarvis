from __future__ import annotations

from typing import Any, Awaitable
from dataclasses import dataclass

from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VoiceControlSkill:
    name: str = "voice_control"
    description: str = "Voice interaction control"

    async def initialize(self, settings) -> None:
        pass

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="voice_on",
                description="Enable voice listening",
                handler=self._voice_on,
                skill_name=self.name,
            ),
            SkillCommand(
                name="voice_off",
                description="Disable voice listening",
                handler=self._voice_off,
                skill_name=self.name,
            ),
            SkillCommand(
                name="voice_test",
                description="Test voice output",
                handler=self._voice_test,
                skill_name=self.name,
            ),
        ]

    async def _voice_on(self) -> str:
        return "Voice listening enabled"

    async def _voice_off(self) -> str:
        return "Voice listening disabled"

    async def _voice_test(self, text: str = "Voice systems operational, Sir.") -> str:
        return f"Speaking: {text}"