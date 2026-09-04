from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class FullstackAgentSkill:
    name: str = "fullstack_agent"
    description: str = "Manage the fullstack-agent installer toolbox: check status, run updates, create launchers, and inspect setup."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings
        self.fullstack_dir: Path | None = None

    def _resolve_paths(self) -> None:
        if self.settings is None:
            self.fullstack_dir = Path("./fullstack-agent").resolve()
            return
        self.fullstack_dir = self._resolve_external_path(
            getattr(self.settings.external, "fullstack_agent_path", "./fullstack-agent"),
            fallback=self.settings.project_root / "fullstack-agent",
        )

    def _resolve_external_path(self, raw: str, fallback: Path) -> Path:
        p = Path(os.path.expanduser(raw)) if raw else fallback
        if not p.is_absolute():
            candidate = Path(__file__).resolve().parent.parent.parent.parent / p
            if candidate.exists():
                return candidate.resolve()
            return Path.cwd() / p
        return p

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="fullstack_agent_status",
                description="Check fullstack-agent toolbox status and installed pieces.",
                handler=self._status,
                skill_name=self.name,
            ),
            SkillCommand(
                name="fullstack_agent_update",
                description="Run update scripts for the fullstack-agent toolbox.",
                handler=self._update,
                skill_name=self.name,
            ),
            SkillCommand(
                name="fullstack_agent_launchers",
                description="Create Desktop launcher shortcuts for the agent stack.",
                handler=self._launchers,
                skill_name=self.name,
            ),
            SkillCommand(
                name="fullstack_agent_setup",
                description="Trigger the fullstack-agent setup wizard.",
                handler=self._setup,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings: Any) -> None:
        self.settings = settings
        self._resolve_paths()

    async def _status(self) -> str:
        self._resolve_paths()
        if not self.fullstack_dir.exists():
            return f"fullstack-agent not found at: {self.fullstack_dir}"

        pieces = {
            "ai-memory-vault": PROJECT_ROOT / "ai-memory-vault",
            "backtalk": PROJECT_ROOT / "backtalk",
            "ai-visualizer": PROJECT_ROOT / "ai-visualizer",
            "barehands": PROJECT_ROOT / "barehands",
        }
        lines = [f"Toolbox: {self.fullstack_dir}"]
        for name, path in pieces.items():
            status = "found" if path.exists() else "missing"
            lines.append(f"  {name}: {status} ({path})")
        return "\n".join(lines)

    async def _update(self, piece: str = "all") -> str:
        self._resolve_paths()
        if sys.platform == "win32":
            script = self.fullstack_dir / "update.bat"
        else:
            script = self.fullstack_dir / "update.sh"

        if not script.exists():
            return f"Update script not found: {script}"

        try:
            proc = await asyncio.create_subprocess_exec(
                str(script),
                piece,
                cwd=str(self.fullstack_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.wait(), timeout=120)
            out = stdout.decode("utf-8", errors="replace") if stdout else ""
            err = stderr.decode("utf-8", errors="replace") if stderr else ""
            lines = [f"Update finished with code {proc.returncode}"]
            if out:
                lines.append(out[:2000])
            if err:
                lines.append("STDERR:")
                lines.append(err[:2000])
            return "\n".join(lines)
        except asyncio.TimeoutError:
            return "Update timed out after 120s."
        except Exception as e:
            logger.error("fullstack-agent update failed: %s", e)
            return f"Update failed: {e}"

    async def _launchers(self, agent_name: str = "Jarvis") -> str:
        self._resolve_paths()
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            return f"Desktop folder not found: {desktop}"

        launchers = []
        if sys.platform == "win32":
            launchers.append(self._write_bat_launcher(desktop, agent_name, "Chat"))
        else:
            launchers.append(self._write_command_launcher(desktop, agent_name, "Chat"))

        created = [str(p) for p in launchers if p]
        if created:
            return f"Created launchers:\n" + "\n".join(created)
        return "No launchers created."

    async def _setup(self) -> str:
        self._resolve_paths()
        readme = self.fullstack_dir / "fullstack-agent.md"
        if not readme.exists():
            return f"Setup guide not found: {readme}"
        return (
            "Run the setup wizard by opening this repo in Claude Code and saying "
            f"'set me up'. Setup guide: {readme}"
        )

    def _write_command_launcher(self, desktop: Path, agent_name: str, mode: str) -> Path | None:
        launcher = desktop / f"{mode} with {agent_name}.command"
        try:
            launcher.write_text(
                "#!/bin/bash\n"
                f'cd "{PROJECT_ROOT}" || exit 1\n'
                f'echo Starting {mode} with {agent_name}...\n',
                encoding="utf-8",
            )
            return launcher
        except Exception as e:
            logger.error("Failed to write launcher %s: %s", launcher, e)
            return None

    def _write_bat_launcher(self, desktop: Path, agent_name: str, mode: str) -> Path | None:
        launcher = desktop / f"{mode} with {agent_name}.bat"
        try:
            launcher.write_text(
                f'@echo off\ncd /d "{PROJECT_ROOT}"\n'
                f'echo Starting {mode} with {agent_name}...\n',
                encoding="utf-8",
            )
            return launcher
        except Exception as e:
            logger.error("Failed to write launcher %s: %s", launcher, e)
            return None


import asyncio
