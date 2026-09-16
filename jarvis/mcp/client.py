from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class MCPTool:
    def __init__(self, name: str, description: str, input_schema: dict[str, Any], server_name: str):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.server_name = server_name


# Built-in MCP servers that can be auto-discovered
_BUILTIN_MCP_SERVERS = {
    "filesystem": {
        "command": sys.executable,
        "args": ["-m", "jarvis.mcp.servers.filesystem", "."],
    },
    "terminal": {
        "command": sys.executable,
        "args": ["-m", "jarvis.mcp.servers.terminal"],
    },
    "git": {
        "command": sys.executable,
        "args": ["-m", "jarvis.mcp.servers.git"],
    },
    "memory": {
        "command": sys.executable,
        "args": ["-m", "jarvis.mcp.servers.memory"],
    },
    "web_search": {
        "command": sys.executable,
        "args": ["-m", "jarvis.mcp.servers.web_search"],
    },
    "browser": {
        "command": sys.executable,
        "args": ["-m", "jarvis.mcp.servers.browser"],
    },
    "desktop": {
        "command": sys.executable,
        "args": ["-m", "jarvis.mcp.servers.desktop"],
    },
}


class MCPClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sessions: dict[str, ClientSession] = {}
        self._stacks: dict[str, AsyncExitStack] = {}
        self.tools: list[MCPTool] = []
        self.is_connected = False

    def _resolve_servers(self) -> dict[str, dict[str, Any]]:
        """Merge user-configured servers with auto-discovered built-ins."""
        servers = dict(self.settings.mcp.servers)
        if self.settings.mcp.auto_discover:
            for name, config in _BUILTIN_MCP_SERVERS.items():
                if name not in servers:
                    servers[name] = config
        return servers

    @classmethod
    def configured_servers(cls, settings: Settings) -> dict[str, dict[str, Any]]:
        return dict(settings.mcp.servers)

    @classmethod
    def add_server(cls, settings: Settings, name: str, command: str, args: list[str]) -> None:
        if not name.strip() or name in {".", ".."} or "/" in name or "\\" in name:
            raise ValueError("MCP server name must be a simple non-empty name")
        if name in settings.mcp.servers:
            raise ValueError(f"MCP server already exists: {name}")
        settings.mcp.servers[name] = {"command": command, "args": args, "env": {}}

    @classmethod
    def remove_server(cls, settings: Settings, name: str) -> bool:
        return settings.mcp.servers.pop(name, None) is not None

    async def connect_all(self) -> None:
        servers = self._resolve_servers()
        for server_name, config in servers.items():
            await self.connect_server(server_name, config)

        self.is_connected = len(self.sessions) > 0
        logger.info(
            f"Connected to {len(self.sessions)} MCP servers ({len(self.tools)} tools)"
            if self.is_connected
            else "No MCP servers connected"
        )

    async def connect_server(self, name: str, config: dict[str, Any]) -> bool:
        try:
            command = config.get("command")
            args = config.get("args", [])
            env = config.get("env", {})

            if not command:
                logger.warning(f"MCP server '{name}' has no command, skipping")
                return False

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env,
            )

            stack = AsyncExitStack()
            read_stream, write_stream = await stack.enter_async_context(stdio_client(server_params))
            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()

            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                self.tools.append(MCPTool(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=getattr(tool, "inputSchema", getattr(tool, "input_schema", {})),
                    server_name=name,
                ))

            self.sessions[name] = session
            self._stacks[name] = stack
            logger.info(f"Connected to MCP server: {name} ({len(tools_result.tools)} tools)")
            return True

        except Exception as e:
            if "stack" in locals():
                await stack.aclose()
            logger.error(f"Failed to connect to MCP server '{name}': {e}")
            return False

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        for tool in self.tools:
            if tool.name == tool_name:
                session = self.sessions.get(tool.server_name)
                if session:
                    try:
                        result = await session.call_tool(tool_name, arguments)
                    except Exception as e:
                        logger.error(f"Tool call failed: {e}")
                        return {"error": str(e)}

                    # MCP tool results may expose content as an attribute or dict key.
                    content = getattr(result, "content", None)
                    if content is None and isinstance(result, dict):
                        content = result.get("content")
                    if content is None:
                        content = result
                    return content
        return {"error": f"Tool not found: {tool_name}"}

    async def list_all_tools(self) -> list[MCPTool]:
        return self.tools

    async def get_available_tool(self, tool_name: str) -> MCPTool | None:
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None

    async def get_available_tools(self) -> list[MCPTool]:
        return self.tools

    async def disconnect_all(self) -> None:
        for name in list(self._stacks):
            try:
                await self._stacks[name].aclose()
            except Exception as e:
                if "cancel scope" in str(e).lower():
                    logger.debug("MCP server %s closed with an AnyIO cancel-scope warning", name)
                else:
                    logger.error(f"Error disconnecting {name}: {e}")
        self.sessions.clear()
        self._stacks.clear()
        self.tools.clear()
        self.is_connected = False
