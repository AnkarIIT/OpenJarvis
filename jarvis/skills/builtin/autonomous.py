from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class AutonomousSkill:
    name: str = "autonomous"
    description: str = "Run autonomous actions: scripts, scheduled tasks, macros, and automated workflows."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings=None):
        self.settings = settings
        self.running_tasks: dict[str, asyncio.Task] = {}
        self.schedules: list[dict] = []

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="auto_run",
                description="Run a script or command autonomously. Usage: auto_run --file script.py or auto_run --cmd 'ls -la'",
                handler=self._run,
                skill_name=self.name,
            ),
            SkillCommand(
                name="auto_schedule",
                description="Schedule a recurring task. Usage: auto_schedule --name backup --cmd 'git pull' --interval 3600",
                handler=self._schedule,
                skill_name=self.name,
            ),
            SkillCommand(
                name="auto_list_schedules",
                description="List all scheduled tasks.",
                handler=self._list_schedules,
                skill_name=self.name,
            ),
            SkillCommand(
                name="auto_stop",
                description="Stop a running autonomous task.",
                handler=self._stop,
                skill_name=self.name,
            ),
            SkillCommand(
                name="auto_macro",
                description="Record and replay a sequence of commands as a macro.",
                handler=self._macro,
                skill_name=self.name,
            ),
            SkillCommand(
                name="auto_status",
                description="Check status of all autonomous tasks.",
                handler=self._status,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings) -> None:
        self.settings = settings

    async def _run(self, file: str = "", cmd: str = "") -> str:
        if file and Path(file).exists():
            try:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, str(file),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.wait(), timeout=300)
                out = stdout.decode("utf-8", errors="replace") if stdout else ""
                return f"Script executed successfully.\nOutput:\n{out[:2000]}" if out else f"Script completed (exit code: {proc.returncode})."
            except asyncio.TimeoutError:
                return "Script timed out after 300s"
            except Exception as e:
                return f"Script error: {e}"
        elif cmd:
            try:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.wait(), timeout=60)
                out = stdout.decode("utf-8", errors="replace") if stdout else ""
                return f"Command executed.\nOutput:\n{out[:2000]}" if out else f"Command completed (code: {proc.returncode})."
            except asyncio.TimeoutError:
                return "Command timed out"
            except Exception as e:
                return f"Command error: {e}"
        return "Error: Provide --file or --cmd"

    async def _schedule(self, name: str = "", cmd: str = "", interval: int = 3600) -> str:
        if not name or not cmd:
            return "Error: --name and --cmd are required"

        task_info = {
            "name": name,
            "cmd": cmd,
            "interval": interval,
            "next_run": time.time() + interval,
            "status": "scheduled",
        }
        self.schedules.append(task_info)

        async def _runner():
            while True:
                await asyncio.sleep(interval)
                try:
                    proc = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await proc.wait()
                    logger.info(f"Scheduled task '{name}' completed")
                except Exception as e:
                    logger.error(f"Scheduled task '{name}' error: {e}")

        task = asyncio.create_task(_runner())
        self.running_tasks[name] = task
        return f"Scheduled '{name}' to run every {interval}s"

    async def _list_schedules(self) -> str:
        if not self.schedules:
            return "No scheduled tasks"
        lines = ["Scheduled Tasks:"]
        for s in self.schedules:
            lines.append(f"  {s['name']}: {s['cmd']} (every {s['interval']}s)")
        return "\n".join(lines)

    async def _stop(self, name: str = "") -> str:
        if name in self.running_tasks:
            self.running_tasks[name].cancel()
            del self.running_tasks[name]
            return f"Stopped task: {name}"
        return f"Task '{name}' not found"

    async def _macro(self, name: str = "", commands: str = "") -> str:
        if not name:
            return "Error: --name is required"
        if not commands:
            return "Error: --commands is required (JSON array of command strings)"

        try:
            cmd_list = json.loads(commands)
            if not isinstance(cmd_list, list):
                return "Error: --commands must be a JSON array"
        except json.JSONDecodeError:
            return "Error: Invalid JSON in --commands"

        macro_file = Path.home() / ".jarvis" / "macros" / f"{name}.json"
        macro_file.parent.mkdir(parents=True, exist_ok=True)
        macro_data = {"name": name, "commands": cmd_list, "created": time.time()}
        macro_file.write_text(json.dumps(macro_data, indent=2))
        return f"Macro '{name}' saved with {len(cmd_list)} commands to {macro_file}"

    async def _status(self) -> str:
        lines = ["Autonomous Tasks:"]
        running = len(self.running_tasks)
        scheduled = len(self.schedules)
        lines.append(f"  Running: {running} | Scheduled: {scheduled}")
        for name, task in self.running_tasks.items():
            status = "running" if not task.done() else "completed"
            lines.append(f"  {name}: {status}")
        if not lines[-1].endswith(":"):
            pass
        return "\n".join(lines)
