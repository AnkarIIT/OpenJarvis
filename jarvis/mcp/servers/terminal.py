from __future__ import annotations

import asyncio
import shlex
from pathlib import Path
from typing import Any

from mcp.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ServerCapabilities

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)

ALLOWED_COMMANDS = {
    "ls", "cat", "grep", "find", "git", "python", "pip", "npm", "node",
    "cargo", "go", "rustc", "docker", "kubectl", "ps", "top", "htop",
    "df", "du", "free", "uname", "whoami", "pwd", "echo",
    "head", "tail", "less", "more", "wc", "sort", "uniq", "awk", "sed",
    "mkdir", "touch", "cp", "mv", "rm", "chmod", "chown", "ln",
    "tar", "gzip", "gunzip", "zip", "unzip", "ssh", "scp", "rsync",
    "curl", "wget", "ping", "traceroute", "dig", "nslookup",
}


def _build_tools() -> list[Tool]:
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


class TerminalMCPServer:
    def __init__(self, allowed_commands: list[str] | None = None):
        self.allowed = set(allowed_commands) if allowed_commands else ALLOWED_COMMANDS
        self.server = Server(
            "terminal",
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool,
        )

    async def _list_tools(self, context: Any, params: Any) -> dict[str, Any]:
        return {"tools": _build_tools()}

    async def _call_tool(self, context: Any, params: Any) -> dict[str, Any]:
        try:
            name = params.name
            arguments = params.arguments or {}
            if name == "run_command":
                return await self._run_command(
                    arguments["command"], arguments.get("cwd", "."), arguments.get("timeout", 30)
                )
            elif name == "run_background":
                return await self._run_background(arguments["command"], arguments.get("cwd", "."))
            return {"content": [TextContent(type="text", text=f"Unknown tool: {name}")]}
        except Exception as e:
            logger.error(f"Terminal tool error: {e}")
            return {"content": [TextContent(type="text", text=f"Error: {str(e)}")]}

    def _is_allowed(self, command: str) -> bool:
        parts = shlex.split(command)
        if not parts:
            return False
        base_cmd = parts[0].split("/")[-1]
        return base_cmd in self.allowed

    async def _run_command(self, command: str, cwd: str, timeout: int) -> dict[str, Any]:
        if not self._is_allowed(command):
            return {"content": [TextContent(type="text", text=f"Command not allowed: {command}")]}

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
                return {"content": [TextContent(type="text", text=f"Command timed out after {timeout}s")]}

            output = []
            if stdout:
                output.append(stdout.decode("utf-8", errors="replace"))
            if stderr:
                output.append(f"STDERR:\n{stderr.decode('utf-8', errors='replace')}")
            output.append(f"Exit code: {process.returncode}")

            joined = chr(10).join(output)
            return {"content": [TextContent(type="text", text=joined)]}

        except Exception as e:
            return {"content": [TextContent(type="text", text=f"Execution error: {str(e)}")]}

    async def _run_background(self, command: str, cwd: str) -> dict[str, Any]:
        if not self._is_allowed(command):
            return {"content": [TextContent(type="text", text=f"Command not allowed: {command}")]}

        try:
            cwd_path = Path(cwd).expanduser().resolve()
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )
            return {"content": [TextContent(type="text", text=f"Started background process (PID: {process.pid})")]}

        except Exception as e:
            return {"content": [TextContent(type="text", text=f"Background execution error: {str(e)}")]}

    async def run(self) -> None:
        options = InitializationOptions(
            server_name="terminal",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools={}),
        )
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, options)


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Terminal MCP Server')
    parser.add_argument('--allow', default='', help='Comma-separated list of allowed commands')
    parser.add_argument('allowed', nargs='*', default=None, help='Allowed commands (positional, for backward compat)')
    args = parser.parse_args()
    if args.allow:
        allowed = [c.strip() for c in args.allow.split(',') if c.strip()]
    elif args.allowed:
        allowed = list(args.allowed)
    else:
        allowed = None
    server = TerminalMCPServer(allowed)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
