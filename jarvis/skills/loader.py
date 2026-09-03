from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any
from dataclasses import dataclass

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Skill:
    name: str
    description: str
    version: str
    author: str
    enabled: bool
    path: Path
    config: dict[str, Any]


class SkillLoader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.skills: dict[str, Skill] = {}

    async def discover_skills(self) -> list[Skill]:
        self.skills.clear()

        for skill_path in self.settings.skills_paths:
            if not skill_path.exists():
                continue

            for skill_dir in skill_path.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    skill_file = skill_dir / "skill.yaml"

                if skill_file.exists():
                    try:
                        skill = await self._load_skill(skill_dir, skill_file)
                        if skill:
                            self.skills[skill.name] = skill
                    except Exception as e:
                        logger.error(f"Failed to load skill from {skill_dir}: {e}")

        return list(self.skills.values())

    async def _load_skill(self, skill_dir: Path, skill_file: Path) -> Skill | None:
        if skill_file.suffix == ".md":
            content = skill_file.read_text(encoding="utf-8")
            config = self._parse_skill_md(content)
        else:
            content = skill_file.read_text(encoding="utf-8")
            config = yaml.safe_load(content)

        if not config:
            return None

        enabled = config.get("name", "") in self.settings.skills.enabled

        return Skill(
            name=config.get("name", skill_dir.name),
            description=config.get("description", ""),
            version=config.get("version", "1.0.0"),
            author=config.get("author", "Unknown"),
            enabled=enabled,
            path=skill_dir,
            config=config,
        )

    def _parse_skill_md(self, content: str) -> dict[str, Any]:
        lines = content.split("\n")
        config = {}
        in_frontmatter = False
        frontmatter_lines = []

        for line in lines:
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                else:
                    break
            if in_frontmatter:
                frontmatter_lines.append(line)

        if frontmatter_lines:
            try:
                config = yaml.safe_load("\n".join(frontmatter_lines))
            except Exception:
                pass

        return config or {}

    async def load_skill(self, name: str) -> Skill | None:
        return self.skills.get(name)

    async def enable_skill(self, name: str) -> bool:
        if name in self.skills:
            self.skills[name].enabled = True
            if name not in self.settings.skills.enabled:
                self.settings.skills.enabled.append(name)
            return True
        return False

    async def disable_skill(self, name: str) -> bool:
        if name in self.skills:
            self.skills[name].enabled = False
            if name in self.settings.skills.enabled:
                self.settings.skills.enabled.remove(name)
            return True
        return False