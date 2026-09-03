from __future__ import annotations

from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field

from jarvis.skills.loader import SkillLoader, Skill
from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SkillCommand:
    name: str
    description: str
    handler: Callable[..., Awaitable[Any]]
    skill_name: str


class SkillRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.loader = SkillLoader(settings)
        self.commands: dict[str, SkillCommand] = {}
        self.skill_instances: dict[str, Any] = {}

    async def initialize(self) -> None:
        await self.loader.discover_skills()
        await self._load_builtin_skills()

    async def _load_builtin_skills(self) -> None:
        from jarvis.skills.builtin.system_monitor import SystemMonitorSkill
        from jarvis.skills.builtin.code_assistant import CodeAssistantSkill
        from jarvis.skills.builtin.memory import MemorySkill
        from jarvis.skills.builtin.voice_control import VoiceControlSkill

        builtin_skills = [
            SystemMonitorSkill(),
            CodeAssistantSkill(),
            MemorySkill(),
            VoiceControlSkill(),
        ]

        for skill in builtin_skills:
            self.skill_instances[skill.name] = skill
            await skill.initialize(self.settings)

    async def get_skill(self, name: str) -> Skill | None:
        return await self.loader.load_skill(name)

    async def enable_skill(self, name: str) -> bool:
        return await self.loader.enable_skill(name)

    async def disable_skill(self, name: str) -> bool:
        return await self.loader.disable_skill(name)

    def register_command(self, command: SkillCommand) -> None:
        self.commands[command.name] = command

    async def execute_command(self, name: str, *args, **kwargs) -> Any:
        if name in self.commands:
            return await self.commands[name].handler(*args, **kwargs)
        raise ValueError(f"Command not found: {name}")

    def list_commands(self) -> list[SkillCommand]:
        return list(self.commands.values())

    def list_skills(self) -> list[Skill]:
        return list(self.loader.skills.values())