from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Button, ListView, ListItem, Label
from textual.reactive import reactive

from jarvis.config.settings import Settings
from jarvis.mcp.client import MCPClient


class ToolsScreen(Screen):
    BINDINGS = [
        ("escape", "back", "Back"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, settings: Settings, mcp_client: MCPClient | None = None):
        super().__init__()
        self.settings = settings
        self.mcp_client = mcp_client or MCPClient(settings)
        self.tools = []

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static("MCP Tools", id="tools-title"),
                Horizontal(
                    Button("Refresh", id="refresh-btn"),
                    Button("Add Server", id="add-btn", variant="primary"),
                    id="tools-actions",
                ),
                ListView(id="tools-list"),
                id="tools-container",
            )
        )

    async def on_mount(self) -> None:
        await self._load_tools()

    async def _load_tools(self) -> None:
        await self.mcp_client.connect_all()
        self.tools = await self.mcp_client.list_all_tools()

        list_view = self.query_one("#tools-list", ListView)
        await list_view.clear()

        for tool in self.tools:
            item = ListItem(
                Horizontal(
                    Label(f"🔧 {tool.name}", classes="tool-name"),
                    Label(tool.description, classes="tool-desc"),
                    classes="tool-item",
                ),
                id=f"tool-{tool.name}",
            )
            await list_view.append(item)

    def action_back(self) -> None:
        self.app.switch_screen("chat")

    def action_refresh(self) -> None:
        self.run_worker(self._load_tools)