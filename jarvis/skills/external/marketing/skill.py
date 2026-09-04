from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Awaitable, Callable

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

PLAYBOOK_FILES = {
    "principles": "jareds-takes.md",
    "copywriting": "marketing-copywriting.md",
    "sales_letter": "marketing-sales-letter.md",
    "email": "marketing-email.md",
    "fb_ads": "marketing-fb-ads.md",
    "lead_magnets": "marketing-lead-magnets.md",
    "content": "marketing-content.md",
    "analytics": "marketing-analytics.md",
    "fundamentals": "the-fundamentals.md",
    "about": "about.md",
    "thesis": "the-thesis.md",
}


class MarketingSkill:
    name: str = "marketing"
    description: str = "Access jaredrhod's marketing playbook for copywriting, sales pages, ads, emails, lead magnets, content, and funnel strategy."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, playbook_dir: Path | None = None, settings: Settings | None = None):
        if settings is not None:
            self.playbook_dir = Path(playbook_dir) if playbook_dir else settings.project_root / "ai-marketing-skills" / "jaredrhod-marketing"
        else:
            self.playbook_dir = playbook_dir or Path("ai-marketing-skills/jaredrhod-marketing")

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="marketing_list",
                description="List available marketing playbooks and frameworks",
                handler=self._list_playbooks,
                skill_name=self.name,
            ),
            SkillCommand(
                name="marketing_read",
                description="Read a specific playbook by name (e.g. principles, copywriting, sales_letter, email, fb_ads, lead_magnets, content, analytics, fundamentals, about, thesis)",
                handler=self._read_playbook,
                skill_name=self.name,
            ),
            SkillCommand(
                name="marketing_status",
                description="Check whether the marketing playbook source files are available",
                handler=self._status,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings: Any) -> None:
        if settings is not None:
            self.settings = settings
            if self.playbook_dir is None:
                self.playbook_dir = settings.project_root / "ai-marketing-skills" / "jaredrhod-marketing"

    async def _list_playbooks(self) -> str:
        if not self.playbook_dir.exists():
            return f"Marketing playbook directory not found: {self.playbook_dir}"

        lines = [f"Marketing playbooks at: {self.playbook_dir}", ""]
        for key, filename in PLAYBOOK_FILES.items():
            path = self.playbook_dir / filename
            status = "OK" if path.exists() else "MISSING"
            lines.append(f"- {key}: {filename} [{status}]")

        lines.append("")
        lines.append("Usage: call marketing_read with one of the keys above.")
        return "\n".join(lines)

    async def _read_playbook(self, playbook_key: str = "") -> str:
        key = playbook_key.strip().lower() or "principles"
        if key not in PLAYBOOK_FILES:
            available = ", ".join(sorted(PLAYBOOK_FILES.keys()))
            return f"Unknown playbook: {key}. Available keys: {available}"

        filename = PLAYBOOK_FILES[key]
        path = self.playbook_dir / filename

        if not path.exists():
            return f"Playbook file not found: {path}"

        try:
            content = path.read_text(encoding="utf-8")
            header = f"=== {key}: {filename} ==="
            return f"{header}\n\n{content}"
        except Exception as e:
            logger.error(f"Failed to read marketing playbook {path}: {e}")
            return f"Error reading playbook: {e}"

    async def _status(self) -> str:
        if not self.playbook_dir.exists():
            return f"Marketing playbook directory not found: {self.playbook_dir}"

        total = len(PLAYBOOK_FILES)
        found = sum(1 for f in PLAYBOOK_FILES.values() if (self.playbook_dir / f).exists())
        return f"Marketing playbook status: {found}/{total} files available at {self.playbook_dir}"
