from __future__ import annotations

import asyncio
import io
import base64
from typing import Any

from mcp.server import Server, InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ServerCapabilities

from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


def _build_tools() -> list[Tool]:
    return [
        Tool(
            name="mouse_move",
            description="Move the mouse cursor to coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X coordinate"},
                    "y": {"type": "number", "description": "Y coordinate"},
                },
                "required": ["x", "y"],
            },
        ),
        Tool(
            name="mouse_click",
            description="Click at coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "X coordinate"},
                    "y": {"type": "number", "description": "Y coordinate"},
                    "button": {"type": "string", "description": "Mouse button", "enum": ["left", "right", "middle"], "default": "left"},
                    "clicks": {"type": "number", "description": "Number of clicks", "default": 1},
                },
            },
        ),
        Tool(
            name="mouse_scroll",
            description="Scroll the mouse wheel",
            inputSchema={
                "type": "object",
                "properties": {
                    "dx": {"type": "number", "description": "Horizontal scroll", "default": 0},
                    "dy": {"type": "number", "description": "Vertical scroll", "default": 3},
                },
            },
        ),
        Tool(
            name="keyboard_type",
            description="Type text on the keyboard",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type"},
                    "interval": {"type": "number", "description": "Interval between keystrokes", "default": 0.05},
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="keyboard_press",
            description="Press a keyboard key or combo (e.g. 'ctrl+c')",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key or combo"},
                },
                "required": ["key"],
            },
        ),
        Tool(
            name="get_screen_size",
            description="Get the screen dimensions",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="screenshot",
            description="Take a screenshot of the current screen",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {"type": "object", "description": "Optional region", "properties": {
                        "x": {"type": "number"},
                        "y": {"type": "number"},
                        "width": {"type": "number"},
                        "height": {"type": "number"},
                    }},
                },
            },
        ),
    ]


class DesktopMCPServer:
    def __init__(self):
        self._pyautogui = None
        self._pillow = None
        self._pygetwindow = None
        self.server = Server(
            "desktop",
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool,
        )

    @property
    def pyautogui(self):
        if self._pyautogui is None:
            import pyautogui
            self._pyautogui = pyautogui
            pyautogui.FAILSAFE = True
        return self._pyautogui

    @property
    def PIL(self):
        if self._pillow is None:
            from PIL import Image
            self._pillow = Image
        return self._pillow

    async def _list_tools(self, context: Any, params: Any) -> dict[str, Any]:
        return {"tools": _build_tools()}

    async def _call_tool(self, context: Any, params: Any) -> dict[str, Any]:
        try:
            name = params.name
            arguments = params.arguments or {}
            handler = getattr(self, f"_tool_{name}", None)
            if handler is None:
                return {"content": [TextContent(type="text", text=f"Unknown tool: {name}")]}
            result = await handler(**arguments)
            return result
        except Exception as e:
            logger.error(f"Desktop tool error: {e}")
            return {"content": [TextContent(type="text", text=f"Error: {str(e)}")]}

    async def _tool_mouse_move(self, x: float, y: float) -> dict[str, Any]:
        self.pyautogui.moveTo(x, y)
        return {"content": [TextContent(type="text", text=f"Mouse moved to ({x}, {y})")]}

    async def _tool_mouse_click(self, x: float = None, y: float = None, button: str = "left", clicks: int = 1) -> dict[str, Any]:
        if x is None or y is None:
            x, y = self.pyautogui.position()
        self.pyautogui.click(x, y, button=button, clicks=clicks)
        return {"content": [TextContent(type="text", text=f"Clicked {button} at ({x}, {y})")]}

    async def _tool_mouse_scroll(self, dx: float = 0, dy: float = 3) -> dict[str, Any]:
        self.pyautogui.scroll(dy, dx=dx)
        return {"content": [TextContent(type="text", text=f"Scrolled dx={dx}, dy={dy}")]}

    async def _tool_keyboard_type(self, text: str, interval: float = 0.05) -> dict[str, Any]:
        self.pyautogui.typewrite(text, interval=interval)
        return {"content": [TextContent(type="text", text=f"Typed: {text[:50]}...")]}

    async def _tool_keyboard_press(self, key: str) -> dict[str, Any]:
        keys = key.split("+")
        if len(keys) > 1:
            self.pyautogui.hotkey(*[k.strip() for k in keys])
        else:
            self.pyautogui.press(key.strip())
        return {"content": [TextContent(type="text", text=f"Pressed: {key}")]}

    async def _tool_get_screen_size(self) -> dict[str, Any]:
        w, h = self.pyautogui.size()
        return {"content": [TextContent(type="text", text=f"Screen: {w}x{h}")]}

    async def _tool_screenshot(self, region: dict[str, float] = None) -> dict[str, Any]:
        if region:
            img = self.pyautogui.screenshot(region=(region["x"], region["y"], region["width"], region["height"]))
        else:
            img = self.pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {"content": [TextContent(type="text", text=f"![Screenshot](data:image/png;base64,{b64[:200]}...)")]}

    async def _close(self):
        self.pyautogui.moveTo(0, 0)
        logger.info("Desktop MCP closed - cursor returned to origin")

    async def run(self) -> None:
        options = InitializationOptions(
            server_name="desktop",
            server_version="1.0.0",
            capabilities=ServerCapabilities(tools={}),
        )
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(read_stream, write_stream, options)
        finally:
            await self._close()


async def main():
    server = DesktopMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
