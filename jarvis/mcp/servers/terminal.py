from __future__ import annotations

import asyncio
import os
import shlex
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

ALLOWED_COMMANDS = {
    "ls", "cat", "grep", "find", "git", "python", "pip", "npm", "node",
    "cargo", "go", "rustc", "docker", "kubectl", "ps", "top", "htop",
    "df", "du", "free", "uname", "whoami", "pwd", "echo", "cat",
    "head", "tail", "less", "more", "wc", "sort", "uniq", "awk", "sed",
    "mkdir", "touch", "cp", "mv", "rm", "chmod", "chown", "ln",
    "tar", "gzip", "gunzip", "zip", "unzip", "ssh", "scp", "rsync",
    "curl", "wget", "ping", "traceroute", "dig", "nslookup",
}


class TerminalMCPServer:
    def __init__(self, allowed_commands: list[str] | None = None):
        self.allowed = set(allowed_commands) if allowed_commands else ALLOWED_COMMANDS
        self.server = Server("terminal")
        self._register_tools()

    def _register_tools(self) -> None:
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="run_command",
                    description="Execute a shell command",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command to execute"},
                            "cwd": {"type": "string", "description": "Working directory", "default": "."},
                            "timeout": {"type": "number", "description": "Timeout in seconds", "default": 30},
                        },
                        "required": ["command"],
                    },
                ),
                Tool(
                    name="run_background",
                    description="Start a background process",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command to execute"},
                            "cwd": {"type": "string", "description": "Working directory", "default": "."},
                        },
                        "required": ["command"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            try:
                if name == "run_command":
                    return await self._run_command(arguments["command"], arguments.get("cwd", "."), arguments.get("timeout", 30))
                elif name == "run_background":
                    return await self._run_background(arguments["command"], arguments.get("cwd", "."))
            except Exception as e:
                logger.error(f"Terminal tool error: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    def _is_allowed(self, command: str) -> bool:
        parts = shlex.split(command)
        if not parts:
            return False
        base_cmd = parts[0].split("/")[-1]
        return base_cmd in self.allowed

    async def _run_command(self, command: str, cwd: str, timeout: int) -> list[TextContent]:
        if not self._is_allowed(command):
            return [TextContent(type="text", text=f"Command not allowed: {command}")]

        try:
            cwd_path = Path(cwd).expanduser().resolve()
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return [TextContent(type="text", text=f"Command timed out after {timeout}s")]

            output = []
            if stdout:
                output.append(stdout.decode("utf-8", errors="replace"))
            if stderr:
                output.append(f"STDERR:\n{stderr.decode('utf-8', errors='replace')}")
            output.append(f"Exit code: {process.returncode}")

            return [TextContent(type="text", text="\n".join(output))]

        except Exception as e:
            return [TextContent(type="text", text=f"Execution error: {str(e)}")]

    async def _run_background(self, command: str, cwd: str) -> list[TextContent]:
        if not self._is_allowed(command):
            return [TextContent(type="text", text=f"Command not allowed: {command}")]

        try:
            cwd_path = Path(cwd).expanduser().resolve()
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
            return [TextContent(type="text", text=f"Started background process (PID: {process.pid})")]

        except Exception as e:
            return [TextContent(type="text", text=f"Background execution error: {str(e)}")]

    async def run(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    import sys
    allowed = sys.argv[1:] if len(sys.argv) > 1 else None
    server = TerminalMCPServer(allowed)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())