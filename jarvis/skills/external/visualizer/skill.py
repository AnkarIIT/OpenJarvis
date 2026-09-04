from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillCommand
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

STATES = {"idle", "listening", "thinking", "speaking"}


class VisualizerSkill:
    name: str = "visualizer"
    description: str = "Launch and control the ai-visualizer faces. Start/stop the server, set face state, run demos, and switch faces."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings
        self.visualizer_dir: Path | None = None
        self.bus_dir: Path | None = None
        self.server_process: asyncio.subprocess.Process | None = None
        self.port = 8790
        self.face = "board"

    def _resolve_paths(self) -> None:
        if self.settings is None:
            return
        self.visualizer_dir = self.settings.external_visualizer_dir
        self.bus_dir = self.settings.external_visualizer_bus_dir
        self.port = self.settings.external.visualizer_port
        self.face = self.settings.external.visualizer_default_face

    def get_commands(self) -> list[SkillCommand]:
        return [
            SkillCommand(
                name="visualizer_start",
                description="Start the ai-visualizer server. Optionally pass mode=demo and face=board|radial|rain|neural.",
                handler=self._start,
                skill_name=self.name,
            ),
            SkillCommand(
                name="visualizer_stop",
                description="Stop the ai-visualizer server if it is running.",
                handler=self._stop,
                skill_name=self.name,
            ),
            SkillCommand(
                name="visualizer_status",
                description="Check whether the visualizer server is running and what state it is in.",
                handler=self._status,
                skill_name=self.name,
            ),
            SkillCommand(
                name="visualizer_set_state",
                description="Set the visualizer face state: idle, listening, thinking, or speaking.",
                handler=self._set_state,
                skill_name=self.name,
            ),
            SkillCommand(
                name="visualizer_set_face",
                description="Switch the default face: board, radial, rain, or neural.",
                handler=self._set_face,
                skill_name=self.name,
            ),
            SkillCommand(
                name="visualizer_demo",
                description="Launch the visualizer in demo mode with a scripted state.",
                handler=self._demo,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings: Any) -> None:
        self.settings = settings
        self._resolve_paths()
        if self.bus_dir is None:
            self.bus_dir = Path("./ai-visualizer/bus").resolve()
        self.bus_dir.mkdir(parents=True, exist_ok=True)
        if self.visualizer_dir is None:
            self.visualizer_dir = Path("./ai-visualizer").resolve()
        await self._write_config()

    async def _start(self, mode: str = "real", face: str = "") -> str:
        self._resolve_paths()
        if self._is_running():
            return f"Visualizer already running at http://127.0.0.1:{self.port}/"

        if face:
            self.face = face

        server_py = self.visualizer_dir / "server.py"
        if not server_py.exists():
            return f"Visualizer server not found: {server_py}"

        cmd = [sys.executable, str(server_py)]
        if mode == "demo":
            cmd += ["--mock", "speaking"]

        try:
            self.server_process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self.visualizer_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            logger.info("Visualizer server started PID=%s", self.server_process.pid)
            return f"Visualizer starting at http://127.0.0.1:{self.port}/ (PID {self.server_process.pid})"
        except Exception as e:
            logger.error("Failed to start visualizer: %s", e)
            return f"Failed to start visualizer: {e}"

    async def _stop(self) -> str:
        if not self.server_process or self.server_process.returncode is not None:
            self.server_process = None
            return "Visualizer is not running."

        try:
            self.server_process.terminate()
            await asyncio.wait_for(self.server_process.wait(), timeout=5)
        except asyncio.TimeoutError:
            self.server_process.kill()
            await self.server_process.wait()
        except Exception as e:
            logger.error("Error stopping visualizer: %s", e)
        finally:
            self.server_process = None
        return "Visualizer stopped."

    async def _status(self) -> str:
        if not self._is_running():
            return "Visualizer is not running."

        try:
            req = Request(f"http://127.0.0.1:{self.port}/state")
            with urlopen(req, timeout=2) as r:
                data = json.loads(r.read().decode())
            state = data.get("state", "unknown")
            loading = data.get("loading", False)
            alert = data.get("alert", False)
            lines = [
                f"Visualizer running at http://127.0.0.1:{self.port}/",
                f"State: {state}",
                f"Loading: {loading}",
                f"Alert: {alert}",
            ]
            return "\n".join(lines)
        except URLError as e:
            return f"Visualizer process exists but HTTP check failed: {e}"
        except Exception as e:
            return f"Status check failed: {e}"

    async def _set_state(self, state: str = "idle") -> str:
        self._resolve_paths()
        state = state.strip().lower()
        if state not in STATES:
            return f"Invalid state: {state}. Use one of: {', '.join(sorted(STATES))}"

        try:
            (self.bus_dir / ".voice_state").write_text(state, encoding="utf-8")
            return f"Visualizer state set to {state}."
        except Exception as e:
            logger.error("Failed to set visualizer state: %s", e)
            return f"Failed to set state: {e}"

    async def _set_face(self, face: str = "") -> str:
        face = face.strip().lower() or self.face
        valid = ["board", "radial", "rain", "neural"]
        if face not in valid:
            return f"Invalid face: {face}. Use one of: {', '.join(valid)}"

        self.face = face
        await self._write_config()
        return f"Default face set to {face}. Restart the visualizer to apply."

    async def _demo(self, face: str = "board") -> str:
        face = face.strip().lower() or "board"
        result = await self._start(mode="demo", face=face)
        return result

    def _is_running(self) -> bool:
        if self.server_process is None:
            return False
        return self.server_process.returncode is None

    async def _write_config(self) -> None:
        if self.visualizer_dir is None or self.bus_dir is None:
            return
        config_path = self.visualizer_dir / "ai-visualizer.json"
        config = {
            "name": "JARVIS",
            "badge": "",
            "face": self.face,
            "port": self.port,
            "bus_dir": str(self.bus_dir),
            "thinking_sound": False,
        }
        try:
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error("Failed to write visualizer config: %s", e)
