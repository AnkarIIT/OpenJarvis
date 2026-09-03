from __future__ import annotations

import asyncio
import json
import uuid
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


class MCPClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sessions: dict[str, ClientSession] = {}
        self.tools: list[MCPTool] = []
        self.is_connected = False

    async def connect_all(self) -> None:
        for server_name, config in self.settings.mcp.servers.items():
            await self.connect_server(server_name, config)

        self.is_connected = len(self.sessions) > 0
        logger.info(f"Connected to {len(self.sessions)} MCP servers")

    async def connect_server(self, name: str, config: dict[str, Any]) -> bool:
        try:
            command = config.get("command")
            args = config.get("args", [])
            env = config.get("env", {})

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env,
            )

            read_stream, write_stream = await stdio_client(server_params).__aenter__()
            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()

            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                self.tools.append(MCPTool(
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.inputSchema,
                    server_name=name,
                ))

            self.sessions[name] = session
            logger.info(f"Connected to MCP server: {name} ({len(tools_result.tools)} tools)")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {name}: {e}")
            return False

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        for tool in self.tools:
            if tool.name == tool_name:
                session = self.sessions.get(tool.server_name)
                if session:
                    try:
                        result = await session.call_tool(tool_name, arguments)
                        return result.content
                    except Exception as e:
                        logger.error(f"Tool call failed: {e}")
                        return {"error": str(e)}
        return {"error": f"Tool not found: {tool_name}"}

    async def list_all_tools(self) -> list[MCPTool]:
        return self.tools

    async def get_available_tools(self) -> list[MCPTool]:
        return self.tools

    async def disconnect_all(self) -> None:
        for name, session in self.sessions.items():
            try:
                await session.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error disconnecting {name}: {e}")
        self.sessions.clear()
        self.tools.clear()
        self.is_connected = False