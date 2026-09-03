from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class GitMCPServer:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).expanduser().resolve()
        self.server = Server("git")
        self._register_tools()

    def _register_tools(self) -> None:
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="git_status",
                    description="Get git status",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="git_diff",
                    description="Get git diff",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "staged": {"type": "boolean", "description": "Show staged changes", "default": False},
                        },
                    },
                ),
                Tool(
                    name="git_log",
                    description="Get git log",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "Number of commits", "default": 10},
                        },
                    },
                ),
                Tool(
                    name="git_branch",
                    description="List branches",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="git_add",
                    description="Stage files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "files": {"type": "array", "items": {"type": "string"}, "description": "Files to stage"},
                        },
                        "required": ["files"],
                    },
                ),
                Tool(
                    name="git_commit",
                    description="Commit staged changes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "Commit message"},
                        },
                        "required": ["message"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            try:
                if name == "git_status":
                    return await self._git_status()
                elif name == "git_diff":
                    return await self._git_diff(arguments.get("staged", False))
                elif name == "git_log":
                    return await self._git_log(arguments.get("limit", 10))
                elif name == "git_branch":
                    return await self._git_branch()
                elif name == "git_add":
                    return await self._git_add(arguments["files"])
                elif name == "git_commit":
                    return await self._git_commit(arguments["message"])
            except Exception as e:
                logger.error(f"Git tool error: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def _run_git(self, *args: str) -> tuple[str, str, int]:
        process = await asyncio.create_subprocess_exec(
            "git", *args,
            cwd=self.repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return stdout.decode("utf-8", errors="replace"), stderr.decode("utf-8", errors="replace"), process.returncode

    async def _git_status(self) -> list[TextContent]:
        stdout, stderr, code = await self._run_git("status", "--short")
        if code != 0:
            return [TextContent(type="text", text=f"Error: {stderr}")]
        return [TextContent(type="text", text=stdout or "Working tree clean")]

    async def _git_diff(self, staged: bool) -> list[TextContent]:
        args = ["diff"]
        if staged:
            args.append("--cached")
        stdout, stderr, code = await self._run_git(*args)
        if code != 0:
            return [TextContent(type="text", text=f"Error: {stderr}")]
        return [TextContent(type="text", text=stdout or "No changes")]

    async def _git_log(self, limit: int) -> list[TextContent]:
        stdout, stderr, code = await self._run_git("log", f"-{limit}", "--oneline", "--graph", "--decorate")
        if code != 0:
            return [TextContent(type="text", text=f"Error: {stderr}")]
        return [TextContent(type="text", text=stdout)]

    async def _git_branch(self) -> list[TextContent]:
        stdout, stderr, code = await self._run_git("branch", "-a")
        if code != 0:
            return [TextContent(type="text", text=f"Error: {stderr}")]
        return [TextContent(type="text", text=stdout)]

    async def _git_add(self, files: list[str]) -> list[TextContent]:
        stdout, stderr, code = await self._run_git("add", *files)
        if code != 0:
            return [TextContent(type="text", text=f"Error: {stderr}")]
        return [TextContent(type="text", text=f"Staged: {', '.join(files)}")]

    async def _git_commit(self, message: str) -> list[TextContent]:
        stdout, stderr, code = await self._run_git("commit", "-m", message)
        if code != 0:
            return [TextContent(type="text", text=f"Error: {stderr}")]
        return [TextContent(type="text", text=stdout)]

    async def run(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else "."
    server = GitMCPServer(repo)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())