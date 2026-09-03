from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from urllib.parse import quote_plus

import httpx

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class WebSearchMCPServer:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("SEARCH_API_KEY")
        self.server = Server("web_search")
        self._register_tools()

    def _register_tools(self) -> None:
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="web_search",
                    description="Search the web",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "num_results": {"type": "integer", "description": "Number of results", "default": 5},
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="fetch_url",
                    description="Fetch content from a URL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL to fetch"},
                        },
                        "required": ["url"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            try:
                if name == "web_search":
                    return await self._web_search(arguments["query"], arguments.get("num_results", 5))
                elif name == "fetch_url":
                    return await self._fetch_url(arguments["url"])
            except Exception as e:
                logger.error(f"Web search tool error: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    async def _web_search(self, query: str, num_results: int) -> list[TextContent]:
        if self.api_key:
            return await self._search_with_api(query, num_results)
        else:
            return await self._search_duckduckgo(query, num_results)

    async def _search_with_api(self, query: str, num_results: int) -> list[TextContent]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.searchapi.io/search",
                json={"q": query, "num": num_results},
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10,
            )
            data = response.json()
            results = data.get("organic_results", [])
            output = []
            for r in results[:num_results]:
                output.append(f"- {r.get('title', '')}: {r.get('snippet', '')} ({r.get('link', '')})")
            return [TextContent(type="text", text="\n".join(output) if output else "No results")]

    async def _search_duckduckgo(self, query: str, num_results: int) -> list[TextContent]:
        async with httpx.AsyncClient() as client:
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = await client.get(url, timeout=10)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            results = []
            for result in soup.select(".result__snippet")[:num_results]:
                text = result.get_text(strip=True)
                if text:
                    results.append(text)

            output = [f"- {r}" for r in results]
            return [TextContent(type="text", text="\n".join(output) if output else "No results (install bs4 for better parsing)")]

    async def _fetch_url(self, url: str) -> list[TextContent]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")
                if "text/html" in content_type:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, "html.parser")
                    for script in soup(["script", "style"]):
                        script.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                    return [TextContent(type="text", text=text[:5000])]
                else:
                    return [TextContent(type="text", text=response.text[:5000])]

            except Exception as e:
                return [TextContent(type="text", text=f"Fetch error: {str(e)}")]

    async def run(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)


async def main():
    import sys
    api_key = sys.argv[1] if len(sys.argv) > 1 else None
    server = WebSearchMCPServer(api_key)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())