from __future__ import annotations

import asyncio
from typing import Any

from mcp.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, ServerCapabilities

from jarvis.utils.logger import get_logger
from jarvis.mcp.compat import serialize_tools, text_result

try:
    from duckduckgo_search import DDGS
    HAS_DDG = True
except Exception:  # pragma: no cover - optional dependency
    HAS_DDG = False

logger = get_logger(__name__)


async def _list_tools(context: Any, params: Any) -> Any:
    return {
        "tools": serialize_tools([
            Tool(
                name="web_search",
                description="Search the web using DuckDuckGo and return top results.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {"type": "integer", "description": "Maximum results to return", "default": 5},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="web_search_news",
                description="Search recent news using DuckDuckGo.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "News search query"},
                        "max_results": {"type": "integer", "description": "Maximum results to return", "default": 5},
                    },
                    "required": ["query"],
                },
            ),
        ])
    }


async def _call_tool(context: Any, params: Any) -> Any:
    try:
        if not HAS_DDG:
            return text_result("duckduckgo-search package is not installed.")
        name = params.name
        arguments = params.arguments or {}
        if name == "web_search":
            return await _search(arguments.get("query", ""), arguments.get("max_results", 5))
        if name == "web_search_news":
            return await _search_news(arguments.get("query", ""), arguments.get("max_results", 5))
        return text_result(f"Unknown tool: {name}")
    except Exception as e:
        logger.error(f"Web search tool error: {e}")
        return text_result(f"Error: {str(e)}")


async def _search(query: str, max_results: int) -> Any:
    if not query:
        return text_result("Missing query.")
    try:
        results: list[str] = []
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                title = item.get("title", "")
                href = item.get("href", "")
                body = item.get("body", "")
                results.append(f"- {title}\n  {href}\n  {body}")
        if not results:
            return text_result("No results found.")
        return text_result("\n\n".join(results))
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return text_result(f"Search failed: {e}")


async def _search_news(query: str, max_results: int) -> Any:
    if not query:
        return text_result("Missing query.")
    try:
        results: list[str] = []
        with DDGS() as ddgs:
            for item in ddgs.news(query, max_results=max_results):
                title = item.get("title", "")
                url = item.get("url", "")
                source = item.get("source", "")
                date = item.get("date", "")
                results.append(f"- {title}\n  Source: {source} | {date}\n  {url}")
        if not results:
            return text_result("No news results found.")
        return text_result("\n\n".join(results))
    except Exception as e:
        logger.error(f"News search failed: {e}")
        return text_result(f"News search failed: {e}")


def create_server() -> Server:
    return Server(
        "web-search",
        on_list_tools=_list_tools,
        on_call_tool=_call_tool,
    )


async def main() -> None:
    server = create_server()
    options = InitializationOptions(
        server_name="web-search",
        server_version="1.0.0",
        capabilities=ServerCapabilities(tools={}),
    )
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


if __name__ == "__main__":
    asyncio.run(main())
