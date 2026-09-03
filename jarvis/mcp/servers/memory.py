from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from jarvis.memory.vector_store import VectorStore
from jarvis.config.settings import Settings
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class MemoryMCPServer:
    def __init__(self, memory_path: str):
        settings = Settings()
        settings.memory.path = memory_path
        self.vector_store = VectorStore(settings)
        self.server = Server("memory")
        self._register_tools()

    def _register_tools(self) -> None:
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
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

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            try:
                await self.vector_store.initialize()
                if name == "add_memory":
                    return await self._add_memory(arguments["content"], arguments.get("metadata", {}))
                elif name == "search_memory":
                    return await self._search_memory(arguments["query"], arguments.get("limit", 5))
                elif name == "list_memories":
                    return await self._list_memories(arguments.get("limit", 10))
                elif name == "delete_memory":
                    return await self._delete_memory(arguments["id"])
            except Exception as e:
                logger.error(f"Memory tool error: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def _add_memory(self, content: str, metadata: dict) -> list[TextContent]:
        memory_id = await self.vector_store.add_memory(content, metadata)
        return [TextContent(type="text", text=f"Memory added with ID: {memory_id}")]

    async def _search_memory(self, query: str, limit: int) -> list[TextContent]:
        results = await self.vector_store.search(query, limit)
        if not results:
            return [TextContent(type="text", text="No memories found")]
        output = []
        for r in results:
            output.append(f"[{r['id']}] {r['content'][:200]}... (score: {r['score']:.2f})")
        return [TextContent(type="text", text="\n".join(output))]

    async def _list_memories(self, limit: int) -> list[TextContent]:
        memories = await self.vector_store.list_memories(limit)
        if not memories:
            return [TextContent(type="text", text="No memories stored")]
        output = []
        for m in memories:
            output.append(f"[{m['id']}] {m['content'][:200]}... ({m['timestamp']})")
        return [TextContent(type="text", text="\n".join(output))]

    async def _delete_memory(self, memory_id: str) -> list[TextContent]:
        await self.vector_store.delete_memory(memory_id)
        return [TextContent(type="text", text=f"Memory {memory_id} deleted")]

    async def run(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "~/.jarvis/memory"
    server = MemoryMCPServer(path)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())