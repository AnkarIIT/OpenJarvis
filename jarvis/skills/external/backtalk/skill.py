from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_PORT = 8794
STATES = {"idle", "listening", "thinking", "speaking"}


class BacktalkSkill:
    name: str = "backtalk"
    description: str = "Control the backtalk voice loop: start/stop the voice server, set ring state, manage config, and check voice status."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings
        self.backtalk_dir: Path | None = None
        self.state_dir: Path | None = None
        self.server_process: asyncio.subprocess.Process | None = None
        self.port = DEFAULT_PORT

    def _resolve_paths(self) -> None:
        if self.settings is None:
            self.backtalk_dir = Path("./backtalk").resolve()
            self.state_dir = self.backtalk_dir / "state"
            return
        self.backtalk_dir = self._resolve_external_path(
            getattr(self.settings.external, "backtalk_path", "./backtalk"),
            fallback=self.settings.project_root / "backtalk",
        )
        self.state_dir = self._resolve_external_path(
            getattr(self.settings.external, "backtalk_state_dir", ""),
            fallback=self.backtalk_dir / "state",
        )
        self.port = int(getattr(self.settings.external, "backtalk_port", DEFAULT_PORT))

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
                name="backtalk_start",
                description="Start the backtalk voice loop subprocess.",
                handler=self._start,
                skill_name=self.name,
            ),
            SkillCommand(
                name="backtalk_stop",
                description="Stop the backtalk voice loop if it is running.",
                handler=self._stop,
                skill_name=self.name,
            ),
            SkillCommand(
                name="backtalk_status",
                description="Check backtalk process status and ring state.",
                handler=self._status,
                skill_name=self.name,
            ),
            SkillCommand(
                name="backtalk_set_state",
                description="Set the voice ring state: idle, listening, thinking, or speaking.",
                handler=self._set_state,
                skill_name=self.name,
            ),
            SkillCommand(
                name="backtalk_set_mood",
                description="Set the ring mood JSON: green, amber, or red.",
                handler=self._set_mood,
                skill_name=self.name,
            ),
            SkillCommand(
                name="backtalk_config",
                description="Read or write backtalk.json config values.",
                handler=self._config,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings: Any) -> None:
        self.settings = settings
        self._resolve_paths()
        if self.state_dir:
            self.state_dir.mkdir(parents=True, exist_ok=True)

    async def _start(self) -> str:
        self._resolve_paths()
        if self._is_running():
            return f"backtalk already running (PID {self.server_process.pid})"

        main_py = self.backtalk_dir / "backtalk" / "main.py"
        if not main_py.exists():
            return f"backtalk main.py not found: {main_py}"

        try:
            self.server_process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(main_py),
                cwd=str(self.backtalk_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            logger.info("backtalk started PID=%s", self.server_process.pid)
            return f"backtalk starting (PID {self.server_process.pid})"
        except Exception as e:
            logger.error("Failed to start backtalk: %s", e)
            return f"Failed to start backtalk: {e}"

    async def _stop(self) -> str:
        if not self.server_process or self.server_process.returncode is not None:
            self.server_process = None
            return "backtalk is not running."

        try:
            self.server_process.terminate()
            await asyncio.wait_for(self.server_process.wait(), timeout=5)
        except asyncio.TimeoutError:
            self.server_process.kill()
            await self.server_process.wait()
        except Exception as e:
            logger.error("Error stopping backtalk: %s", e)
        finally:
            self.server_process = None
        return "backtalk stopped."

    async def _status(self) -> str:
        running = self._is_running()
        lines = [f"Process: {'running' if running else 'not running'}"]

        if running:
            lines.append(f"PID: {self.server_process.pid}")

        # Try HTTP API first, fall back to file-based state
        if running:
            try:
                req = Request(f"http://127.0.0.1:{self.port}/state")
                with urlopen(req, timeout=2) as r:
                    data = json.loads(r.read().decode())
                lines.append(f"Ring state: {data.get('state', 'unknown')}")
                lines.append(f"Mood: {data.get('mood', 'unknown')}")
            except Exception:
                pass

        try:
            s = (self.state_dir / "state").read_text(encoding="utf-8").strip().lower()
            if s in STATES:
                lines.append(f"Ring state (file): {s}")
        except Exception:
            lines.append("Ring state: unavailable")

        try:
            m = json.loads((self.state_dir / "mood.json").read_text())
            lines.append(f"Mood (file): {m.get('mood', 'unknown')}")
        except Exception:
            lines.append("Mood: unavailable")

        return "\n".join(lines)

    async def _set_state(self, state: str = "idle") -> str:
        self._resolve_paths()
        state = state.strip().lower()
        if state not in STATES:
            return f"Invalid state: {state}. Use one of: {', '.join(sorted(STATES))}"

        # Try HTTP API first (if server is running), fall back to file-based
        if self._is_running():
            try:
                req = Request(
                    f"http://127.0.0.1:{self.port}/state",
                    data=json.dumps({"state": state}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(req, timeout=2) as r:
                    if r.status == 200:
                        return f"backtalk state set to {state} (via HTTP)."
            except Exception:
                pass

        # Fall back to file-based state
        try:
            (self.state_dir / "state").write_text(state, encoding="utf-8")
            return f"backtalk state set to {state}."
        except Exception as e:
            logger.error("Failed to set backtalk state: %s", e)
            return f"Failed to set state: {e}"

    async def _set_mood(self, mood: str = "green") -> str:
        self._resolve_paths()
        mood = mood.strip().lower()
        if mood not in {"green", "amber", "red"}:
            return f"Invalid mood: {mood}. Use one of: green, amber, red"

        payload = {"mood": mood, "ts": asyncio.get_event_loop().time()}

        # Try HTTP API first
        if self._is_running():
            try:
                req = Request(
                    f"http://127.0.0.1:{self.port}/mood",
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(req, timeout=2) as r:
                    if r.status == 200:
                        return f"backtalk mood set to {mood} (via HTTP)."
            except Exception:
                pass

        # Fall back to file-based state
        try:
            (self.state_dir / "mood.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            return f"backtalk mood set to {mood}."
        except Exception as e:
            logger.error("Failed to set backtalk mood: %s", e)
            return f"Failed to set mood: {e}"

    async def _config(self, action: str = "read", key: str = "", value: str = "") -> str:
        self._resolve_paths()
        config_path = self.backtalk_dir / "backtalk.json"
        if action == "read":
            if not config_path.exists():
                return f"Config not found: {config_path}"
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                if key:
                    return f"{key}: {data.get(key, '<not set>')}"
                return json.dumps(data, indent=2)
            except Exception as e:
                return f"Failed to read config: {e}"

        if action == "write":
            if not key:
                return "Missing required argument: key"
            try:
                data = {}
                if config_path.exists():
                    data = json.loads(config_path.read_text(encoding="utf-8"))
                data[key] = value
                config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                return f"Wrote backtalk config: {key}={value}"
            except Exception as e:
                logger.error("Failed to write backtalk config: %s", e)
                return f"Failed to write config: {e}"

        return f"Unknown config action: {action}. Use read or write."

    def _is_running(self) -> bool:
        if self.server_process is None:
            return False
        return self.server_process.returncode is None
