from __future__ import annotations

import asyncio
from typing import Any

from mcp.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ServerCapabilities

from jarvis.memory.vector_store import VectorStore
from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


def _build_tools() -> list[Tool]:
    return [
        Tool(
            name="add_memory",
            description="Add a memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content"},
                    "metadata": {"type": "object", "description": "Optional metadata"},
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="search_memory",
            description="Search memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="list_memories",
            description="List recent memories",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max results", "default": 10},
                },
            },
        ),
        Tool(
            name="delete_memory",
            description="Delete a memory by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Memory ID"},
                },
                "required": ["id"],
            },
        ),
    ]


class MemoryMCPServer:
    def __init__(self, memory_path: str):
        settings = Settings()
        settings.memory.path = memory_path
        self.vector_store = VectorStore(settings)
        self.server = Server(
            "memory",
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool,
        )

    async def _list_tools(self, context: Any, params: Any) -> dict[str, Any]:
        return {"tools": _build_tools()}

    async def _call_tool(self, context: Any, params: Any) -> dict[str, Any]:
        try:
            await self.vector_store.initialize()
            name = params.name
            arguments = params.arguments or {}
            if name == "add_memory":
                return await self._add_memory(arguments["content"], arguments.get("metadata", {}))
            elif name == "search_memory":
                return await self._search_memory(arguments["query"], arguments.get("limit", 5))
            elif name == "list_memories":
                return await self._list_memories(arguments.get("limit", 10))
            elif name == "delete_memory":
                return await self._delete_memory(arguments["id"])
            return {"content": [TextContent(type="text", text=f"Unknown tool: {name}")]}
        except Exception as e:
            logger.error(f"Memory tool error: {e}")
            return {"content": [TextContent(type="text", text=f"Error: {str(e)}")]}

    async def _add_memory(self, content: str, metadata: dict) -> dict[str, Any]:
        memory_id = await self.vector_store.add_memory(content, metadata)
        return {"content": [TextContent(type="text", text=f"Memory added with ID: {memory_id}")]}

    async def _search_memory(self, query: str, limit: int) -> dict[str, Any]:
        results = await self.vector_store.search(query, limit)
        if not results:
            return {"content": [TextContent(type="text", text="No memories found")]}
        output = []
        for r in results:
            output.append(f"[{r['id']}] {r['content'][:200]}... (score: {r['score']:.2f})")
        return {"content": [TextContent(type="text", text="\n".join(output))]}

    async def _list_memories(self, limit: int) -> dict[str, Any]:
        memories = await self.vector_store.list_memories(limit)
        if not memories:
            return {"content": [TextContent(type="text", text="No memories stored")]}
        output = []
        for m in memories:
            output.append(f"[{m['id']}] {m['content'][:200]}... ({m['timestamp']})")
        return {"content": [TextContent(type="text", text="\n".join(output))]}

    async def _delete_memory(self, memory_id: str) -> dict[str, Any]:
        await self.vector_store.delete_memory(memory_id)
        return {"content": [TextContent(type="text", text=f"Memory {memory_id} deleted")]}

    async def run(self) -> None:
        options = InitializationOptions(
            server_name="memory",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools={}),
        )
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, options)


async def main():
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "~/.jarvis/memory"
    server = MemoryMCPServer(path)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
