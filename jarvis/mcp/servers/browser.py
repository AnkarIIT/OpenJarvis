from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any

from mcp.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ServerCapabilities

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


def _build_tools() -> list[Tool]:
    return [
        Tool(
            name="browser_navigate",
            description="Navigate to a URL in the browser",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to navigate to"},
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="browser_click",
            description="Click an element on the page by CSS selector",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the element to click"},
                },
                "required": ["selector"],
            },
        ),
        Tool(
            name="browser_type",
            description="Type text into an element by CSS selector",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the input element"},
                    "text": {"type": "string", "description": "Text to type"},
                    "clear": {"type": "boolean", "description": "Clear existing text first", "default": True},
                },
                "required": ["selector", "text"],
            },
        ),
        Tool(
            name="browser_screenshot",
            description="Take a screenshot of the current page",
            inputSchema={
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "description": "Capture full scrollable page", "default": False},
                },
            },
        ),
        Tool(
            name="browser_scroll",
            description="Scroll the page",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "description": "Scroll direction", "enum": ["down", "up"]},
                    "amount": {"type": "number", "description": "Scroll amount in pixels", "default": 500},
                },
                "required": ["direction"],
            },
        ),
        Tool(
            name="browser_go_back",
            description="Go back to the previous page",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_go_forward",
            description="Go forward to the next page",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_get_content",
            description="Get the text content of the current page",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_get_title",
            description="Get the title of the current page",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="browser_wait",
            description="Wait for a selector to appear",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector to wait for"},
                    "timeout": {"type": "number", "description": "Timeout in milliseconds", "default": 5000},
                },
                "required": ["selector"],
            },
        ),
    ]


class BrowserMCPServer:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._page = None
        self._browser = None
        self.server = Server(
            "browser",
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool,
        )

    @property
    def playwright(self):
        if self._playwright is None:
            from playwright.async_api import async_playwright
            self._playwright = async_playwright()
        return self._playwright

    async def _ensure_browser(self):
        """Lazily launch the browser on first tool call."""
        if self._browser is None or self._browser.is_closed:
            p = await self.playwright.start()
            self._browser = await p.chromium.launch(headless=self.headless)
            self._page = await self._browser.new_page()
            logger.info("Browser launched (headless=%s)", self.headless)

    async def _list_tools(self, context: Any, params: Any) -> dict[str, Any]:
        return {"tools": _build_tools()}

    async def _call_tool(self, context: Any, params: Any) -> dict[str, Any]:
        try:
            await self._ensure_browser()
            name = params.name
            arguments = params.arguments or {}
            handler = getattr(self, f"_tool_{name}", None)
            if handler is None:
                return {"content": [TextContent(type="text", text=f"Unknown tool: {name}")]}
            result = await handler(**arguments)
            return result
        except Exception as e:
            logger.error(f"Browser tool error: {e}")
            return {"content": [TextContent(type="text", text=f"Error: {str(e)}")]}

    async def _tool_browser_navigate(self, url: str) -> dict[str, Any]:
        await self._page.goto(url, wait_until="networkidle")
        return {"content": [TextContent(type="text", text=f"Navigated to: {url}")]}

    async def _tool_browser_click(self, selector: str) -> dict[str, Any]:
        await self._page.click(selector)
        return {"content": [TextContent(type="text", text=f"Clicked: {selector}")]}

    async def _tool_browser_type(self, selector: str, text: str, clear: bool = True) -> dict[str, Any]:
        if clear:
            await self._page.fill(selector, "")
        await self._page.fill(selector, text)
        return {"content": [TextContent(type="text", text=f"Typed into {selector}: {text[:50]}...")]}

    async def _tool_browser_screenshot(self, full_page: bool = False) -> dict[str, Any]:
        img_bytes = await self._page.screenshot(full_page=full_page)
        b64 = base64.b64encode(img_bytes).decode()
        return {"content": [TextContent(type="text", text=f"![Screenshot](data:image/png;base64,{b64[:200]}...)")]}

    async def _tool_browser_scroll(self, direction: str, amount: float = 500) -> dict[str, Any]:
        delta = amount if direction == "down" else -amount
        await self._page.mouse.wheel(0, delta)
        return {"content": [TextContent(type="text", text=f"Scrolled {direction} by {amount}px")]}

    async def _tool_browser_go_back(self) -> dict[str, Any]:
        await self._page.go_back()
        return {"content": [TextContent(type="text", text="Went back")]}

    async def _tool_browser_go_forward(self) -> dict[str, Any]:
        await self._page.go_forward()
        return {"content": [TextContent(type="text", text="Went forward")]}

    async def _tool_browser_get_content(self) -> dict[str, Any]:
        content = await self._page.inner_text("body")
        return {"content": [TextContent(type="text", text=content[:5000])]}

    async def _tool_browser_get_title(self) -> dict[str, Any]:
        title = await self._page.title()
        return {"content": [TextContent(type="text", text=title)]}

    async def _tool_browser_wait(self, selector: str, timeout: float = 5000) -> dict[str, Any]:
        await self._page.wait_for_selector(selector, timeout=timeout)
        return {"content": [TextContent(type="text", text=f"Waited for: {selector}")]}

    async def _close(self):
        if self._browser and not self._browser.is_closed:
            await self._browser.close()
            self._browser = None
            logger.info("Browser closed")

    async def run(self) -> None:
        options = InitializationOptions(
            server_name="browser",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools={}),
        )
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(read_stream, write_stream, options)
        finally:
            await self._close()


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Browser MCP Server (Playwright)')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser headless')
    parser.add_argument('--headed', action='store_true', help='Run browser with visible window')
    args = parser.parse_args()
    server = BrowserMCPServer(headless=args.headless and not args.headed)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
