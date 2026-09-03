from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class FilesystemMCPServer:
    def __init__(self, root_path: str):
        self.root = Path(root_path).expanduser().resolve()
        self.server = Server("filesystem")
        self._register_tools()

    def _register_tools(self) -> None:
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="read_file",
                    description="Read contents of a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to root"},
                        },
                        "required": ["path"],
                    },
                ),
                Tool(
                    name="write_file",
                    description="Write content to a file",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to root"},
                            "content": {"type": "string", "description": "Content to write"},
                        },
                        "required": ["path", "content"],
                    },
                ),
                Tool(
                    name="list_directory",
                    description="List contents of a directory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Directory path relative to root", "default": "."},
                        },
                    },
                ),
                Tool(
                    name="glob",
                    description="Find files matching a pattern",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "Glob pattern"},
                            "path": {"type": "string", "description": "Base path", "default": "."},
                        },
                        "required": ["pattern"],
                    },
                ),
                Tool(
                    name="file_exists",
                    description="Check if a file exists",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "File path relative to root"},
                        },
                        "required": ["path"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            try:
                if name == "read_file":
                    return await self._read_file(arguments["path"])
                elif name == "write_file":
                    return await self._write_file(arguments["path"], arguments["content"])
                elif name == "list_directory":
                    return await self._list_directory(arguments.get("path", "."))
                elif name == "glob":
                    return await self._glob(arguments["pattern"], arguments.get("path", "."))
                elif name == "file_exists":
                    return await self._file_exists(arguments["path"])
            except Exception as e:
                logger.error(f"Filesystem tool error: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    def _resolve_path(self, path: str) -> Path:
        target = (self.root / path).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"Path {path} is outside root directory")
        return target

    async def _read_file(self, path: str) -> list[TextContent]:
        file_path = self._resolve_path(path)
        if not file_path.exists():
            return [TextContent(type="text", text=f"File not found: {path}")]
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return [TextContent(type="text", text=content)]

    async def _write_file(self, path: str, content: str) -> list[TextContent]:
        file_path = self._resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return [TextContent(type="text", text=f"Written to {path}")]

    async def _list_directory(self, path: str) -> list[TextContent]:
        dir_path = self._resolve_path(path)
        if not dir_path.is_dir():
            return [TextContent(type="text", text=f"Not a directory: {path}")]
        items = []
        for item in sorted(dir_path.iterdir()):
            prefix = "📁" if item.is_dir() else "📄"
            items.append(f"{prefix} {item.name}")
        return [TextContent(type="text", text="\n".join(items))]

    async def _glob(self, pattern: str, path: str) -> list[TextContent]:
        base_path = self._resolve_path(path)
        matches = list(base_path.rglob(pattern))
        items = [str(m.relative_to(self.root)) for m in matches]
        return [TextContent(type="text", text="\n".join(items) if items else "No matches")]

    async def _file_exists(self, path: str) -> list[TextContent]:
        file_path = self._resolve_path(path)
        return [TextContent(type="text", text=str(file_path.exists()))]

    async def run(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "~"
    server = FilesystemMCPServer(root)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())