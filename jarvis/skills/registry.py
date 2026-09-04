from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
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
        await self._load_external_skills()

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
            self._register_skill_commands(skill)

    async def _load_external_skills(self) -> None:
        for skill_meta in self.loader.skills.values():
            if skill_meta.enabled is False:
                continue

            skill_py = skill_meta.path / "skill.py"
            if not skill_py.exists():
                logger.warning(f"External skill missing skill.py: {skill_meta.path}")
                continue

            try:
                spec = importlib.util.spec_from_file_location(
                    f"jarvis.skills.external.{skill_meta.name}",
                    skill_py,
                )
                module = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = module
                spec.loader.exec_module(module)

                # Heuristic: look for a class with get_commands()
                skill_instance = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and hasattr(attr, "get_commands"):
                        skill_instance = attr()
                        break

                if skill_instance is None:
                    logger.warning(f"No skill class found in {skill_py}")
                    continue

                self.skill_instances[skill_meta.name] = skill_instance
                if hasattr(skill_instance, "initialize"):
                    await skill_instance.initialize(self.settings)
                self._register_skill_commands(skill_instance)
            except Exception as e:
                logger.error(f"Failed to load external skill {skill_meta.name}: {e}")

    def _register_skill_commands(self, skill_instance: Any) -> None:
        if not hasattr(skill_instance, "get_commands"):
            return
        for cmd in skill_instance.get_commands():
            self.register_command(cmd)

    async def get_skill(self, name: str) -> Skill | None:
        return await self.loader.load_skill(name)

    async def enable_skill(self, name: str) -> bool:
        ok = await self.loader.enable_skill(name)
        if ok:
            try:
                from jarvis.config.settings import save_settings
                save_settings(self.settings)
            except Exception as e:
                logger.error(f"Failed to persist skill enable: {e}")
        return ok

    async def disable_skill(self, name: str) -> bool:
        ok = await self.loader.disable_skill(name)
        if ok:
            try:
                from jarvis.config.settings import save_settings
                save_settings(self.settings)
            except Exception as e:
                logger.error(f"Failed to persist skill disable: {e}")
        return ok

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