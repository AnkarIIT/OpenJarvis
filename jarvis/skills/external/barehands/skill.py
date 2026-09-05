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
ALLOWED_ACTIONS = {
    "add_img",
    "add_card",
    "clear",
    "reset",
    "hand",
    "give",
    "yank",
    "hover",
    "scroll_note",
    "widget",
    "explode",
    "assemble",
    "present",
}


class BarehandsSkill:
    name: str = "barehands"
    description: str = "Control the barehands air-board: start/stop the hand-tracking server, present cards and media, read board state, and control the assistant ring."
    version: str = "1.0.0"
    author: str = "OpenJarvis"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings
        self.barehands_dir: Path | None = None
        self.state_dir: Path | None = None
        self.server_process: asyncio.subprocess.Process | None = None
        self.port = DEFAULT_PORT

    def _resolve_paths(self) -> None:
        if self.settings is None:
            self.barehands_dir = Path("./barehands").resolve()
            self.state_dir = self.barehands_dir / "state"
            return
        self.barehands_dir = self._resolve_external_path(
            getattr(self.settings.external, "barehands_path", "./barehands"),
            fallback=self.settings.project_root / "barehands",
        )
        self.state_dir = self._resolve_external_path(
            getattr(self.settings.external, "barehands_state_dir", ""),
            fallback=self.barehands_dir / "state",
        )
        self.port = int(getattr(self.settings.external, "barehands_port", DEFAULT_PORT))

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
                name="barehands_start",
                description="Start the barehands server. Optionally pass port.",
                handler=self._start,
                skill_name=self.name,
            ),
            SkillCommand(
                name="barehands_stop",
                description="Stop the barehands server if it is running.",
                handler=self._stop,
                skill_name=self.name,
            ),
            SkillCommand(
                name="barehands_status",
                description="Check barehands server status, board contents, and ring state.",
                handler=self._status,
                skill_name=self.name,
            ),
            SkillCommand(
                name="barehands_cmd",
                description="Send a board command. Provide action and optional JSON payload.",
                handler=self._cmd,
                skill_name=self.name,
            ),
            SkillCommand(
                name="barehands_present",
                description="Present a card on stage with title and optional body.",
                handler=self._present,
                skill_name=self.name,
            ),
            SkillCommand(
                name="barehands_set_state",
                description="Set the assistant ring state: idle, listening, thinking, or speaking.",
                handler=self._set_state,
                skill_name=self.name,
            ),
        ]

    async def initialize(self, settings: Any) -> None:
        self.settings = settings
        self._resolve_paths()
        if self.state_dir:
            self.state_dir.mkdir(parents=True, exist_ok=True)

    async def _start(self, port: str = "") -> str:
        self._resolve_paths()
        if self._is_running():
            return f"barehands already running at http://127.0.0.1:{self.port}/stage.html"

        if port:
            self.port = int(port)

        server_py = self.barehands_dir / "server.py"
        if not server_py.exists():
            return f"barehands server not found: {server_py}"

        try:
            self.server_process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(server_py),
                str(self.port),
                cwd=str(self.barehands_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            logger.info("barehands server started PID=%s", self.server_process.pid)
            return (
                f"barehands starting at http://127.0.0.1:{self.port}/stage.html "
                f"(PID {self.server_process.pid})"
            )
        except Exception as e:
            logger.error("Failed to start barehands: %s", e)
            return f"Failed to start barehands: {e}"

    async def _stop(self) -> str:
        if not self.server_process or self.server_process.returncode is not None:
            self.server_process = None
            return "barehands is not running."

        try:
            self.server_process.terminate()
            await asyncio.wait_for(self.server_process.wait(), timeout=5)
        except asyncio.TimeoutError:
            self.server_process.kill()
            await self.server_process.wait()
        except Exception as e:
            logger.error("Error stopping barehands: %s", e)
        finally:
            self.server_process = None
        return "barehands stopped."

    async def _status(self) -> str:
        server_running = self._is_running()
        lines = [f"Server: {'running' if server_running else 'not running'} at http://127.0.0.1:{self.port}/stage.html"]

        if server_running:
            board = await self._read_board_state()
            lines.append(f"Board items: {board.get('count', 0)}")
            for item in board.get("items", [])[:8]:
                lines.append(f"  - {item}")
            if board.get("count", 0) > 8:
                lines.append(f"  ... and {board.get('count', 0) - 8} more")

            ring = await self._read_ring_state()
            lines.append(f"Ring state: {ring.get('state', 'unknown')}")
            lines.append(f"Ring mood: {ring.get('mood', 'unknown')}")
        else:
            lines.append(f"Open Chrome to http://127.0.0.1:{self.port}/stage.html to use the board.")

        return "\n".join(lines)

    async def _cmd(self, action: str = "", payload: str = "") -> str:
        self._resolve_paths()
        action = action.strip().lower()
        if action not in ALLOWED_ACTIONS:
            return f"Invalid action: {action}. Allowed: {', '.join(sorted(ALLOWED_ACTIONS))}"

        cmd: dict[str, Any] = {"a": action}
        if payload:
            try:
                extra = json.loads(payload)
                if isinstance(extra, dict):
                    cmd.update(extra)
            except json.JSONDecodeError:
                return f"Invalid JSON payload: {payload}"

        try:
            req = Request(
                f"http://127.0.0.1:{self.port}/cmd",
                data=json.dumps(cmd).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=5) as r:
                status = r.status
            if status == 204:
                return f"Board command accepted: {action}"
            return f"Board command returned status {status}"
        except URLError as e:
            return f"Board command failed (is server running?): {e}"
        except Exception as e:
            logger.error("barehands cmd failed: %s", e)
            return f"Board command failed: {e}"

    async def _present(self, title: str = "", body: str = "") -> str:
        cmd: dict[str, Any] = {"a": "present", "title": title or "Untitled"}
        if body:
            cmd["body"] = body
        return await self._cmd("present", json.dumps(cmd))

    async def _set_state(self, state: str = "idle") -> str:
        self._resolve_paths()
        state = state.strip().lower()
        if state not in {"idle", "listening", "thinking", "speaking"}:
            return f"Invalid state: {state}. Use one of: idle, listening, thinking, speaking"

        try:
            (self.state_dir / "state").write_text(state, encoding="utf-8")
            return f"Ring state set to {state}."
        except Exception as e:
            logger.error("Failed to set ring state: %s", e)
            return f"Failed to set ring state: {e}"

    def _is_running(self) -> bool:
        if self.server_process is None:
            return False
        return self.server_process.returncode is None

    async def _read_board_state(self) -> dict[str, Any]:
        try:
            req = Request(f"http://127.0.0.1:{self.port}/state")
            with urlopen(req, timeout=2) as r:
                data = json.loads(r.read().decode())
            items = data.get("items") or []
            summaries = []
            for item in items[:20]:
                t = item.get("type", "?")
                title = item.get("title") or item.get("src") or "untitled"
                summaries.append(f"{t}: {title}")
            return {"count": len(items), "items": summaries, "raw": data}
        except Exception as e:
            return {"count": 0, "items": [f"unavailable ({e})"], "raw": {}}

    async def _read_ring_state(self) -> dict[str, Any]:
        try:
            req = Request(f"http://127.0.0.1:{self.port}/orb")
            with urlopen(req, timeout=2) as r:
                return json.loads(r.read().decode())
        except Exception:
            try:
                s = (self.state_dir / "state").read_text(encoding="utf-8").strip().lower()
                if s in {"idle", "listening", "thinking", "speaking"}:
                    return {"state": s, "mood": "unknown"}
            except Exception:
                pass
            return {"state": "unknown", "mood": "unknown"}
