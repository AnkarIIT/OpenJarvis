from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Static, Button, Label, ListView, ListItem, Select, Input, Header
from textual.reactive import reactive
from textual import on

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillRegistry, SkillCommand
from jarvis.mcp.client import MCPClient, MCPTool
from jarvis.agent.loop import AgentLoop
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class SkillCard(ListItem):
    """A selectable card showing a skill/tool with name, description, and status."""

    def __init__(self, name: str, description: str, category: str,
                 enabled: bool = True, command_count: int = 0, id_str: str = ""):
        self.name = name
        self.description = description
        self.category = category
        self.enabled = enabled
        self.command_count = command_count
        super().__init__(
            Horizontal(
                Label(f"{'✅' if enabled else '⬜'} {name}", classes="skill-card-name"),
                Label(f"[{category}] {description}", classes="skill-card-desc"),
                Label(f"{command_count} cmds", classes="skill-card-count"),
                classes="skill-card",
            ),
            id=id_str,
        )


class SetupScreen(Screen):
    """Feynman-style setup screen: shows all skills and tools, user selects what they need."""

    BINDINGS = [
        ("escape", "back", "Back"),
        ("ctrl+s", "save", "Save & Start"),
        ("ctrl+a", "select_all", "Select All"),
        ("ctrl+d", "deselect_all", "Deselect All"),
        ("enter", "toggle_selected", "Toggle"),
    ]

    def __init__(self, settings: Settings, skill_registry: SkillRegistry, mcp_client: MCPClient, agent_loop: AgentLoop):
        super().__init__()
        self.settings = settings
        self.skill_registry = skill_registry
        self.mcp_client = mcp_client
        self.agent_loop = agent_loop
        self.all_items: list[dict] = []
        self.selected_items: set[str] = set()
        self.category_counts: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Static("⚡ JARVIS Setup", id="setup-title"),
                Static("Select the skills and tools you want to use. JARVIS will only load what you choose.", id="setup-subtitle"),
                Horizontal(
                    Button("Select All", id="select-all-btn", variant="primary"),
                    Button("Deselect All", id="deselect-all-btn"),
                    Button("Save & Start", id="save-btn", variant="success"),
                    id="setup-actions",
                ),
                Label("Built-in Skills:", classes="section-label"),
                ListView(id="builtin-skills-list"),
                Label("External Skills:", classes="section-label"),
                ListView(id="external-skills-list"),
                Label("MCP Tools:", classes="section-label"),
                ListView(id="mcp-tools-list"),
                Horizontal(
                    Label("Selected: 0", id="selected-count"),
                    Label("Total: 0", id="total-count"),
                    id="setup-footer",
                ),
                id="setup-container",
            ),
            id="setup-screen",
        )

    async def on_mount(self) -> None:
        await self._load_all_items()

    async def _load_all_items(self) -> None:
        """Load all skills, external skills, and MCP tools into the UI."""
        self.all_items = []
        self.selected_items = set()
        self.category_counts = {}

        # Load builtin skills
        builtin_list = self.query_one("#builtin-skills-list", ListView)
        await builtin_list.clear()

        registry_cmds = self.skill_registry.list_commands()
        skill_instances = getattr(self.skill_registry, "skill_instances", {})

        for skill_name, skill_obj in skill_instances.items():
            cmds = [c for c in registry_cmds if c.skill_name == skill_name]
            enabled = skill_name in self.settings.skills.enabled
            card = SkillCard(
                name=skill_name,
                description=getattr(skill_obj, "description", ""),
                category="Built-in",
                enabled=enabled,
                command_count=len(cmds),
                id_str=f"builtin-{skill_name}",
            )
            await builtin_list.append(card)
            self.all_items.append({"type": "builtin", "name": skill_name, "card": card})
            if enabled:
                self.selected_items.add(f"builtin-{skill_name}")

        self.category_counts["builtin"] = len(skill_instances)

        # Load external skills
        external_list = self.query_one("#external-skills-list", ListView)
        await external_list.clear()

        external_skills = await self.skill_registry.loader.discover_skills()
        for skill in external_skills:
            enabled = skill.name in self.settings.skills.enabled
            card = SkillCard(
                name=skill.name,
                description=skill.description,
                category="External",
                enabled=enabled,
                command_count=len([c for c in registry_cmds if c.skill_name == skill.name]),
                id_str=f"external-{skill.name}",
            )
            await external_list.append(card)
            self.all_items.append({"type": "external", "name": skill.name, "card": card})
            if enabled:
                self.selected_items.add(f"external-{skill.name}")

        self.category_counts["external"] = len(external_skills)

        # Load MCP tools
        tools_list = self.query_one("#mcp-tools-list", ListView)
        await tools_list.clear()

        await self.mcp_client.connect_all()
        mcp_tools = await self.mcp_client.list_all_tools()

        # Group tools by server
        tools_by_server: dict[str, list[MCPTool]] = {}
        for tool in mcp_tools:
            server = tool.server_name
            tools_by_server.setdefault(server, []).append(tool)

        for server_name, tools in tools_by_server.items():
            for tool in tools:
                card = SkillCard(
                    name=f"{server_name}/{tool.name}",
                    description=tool.description[:80],
                    category=f"MCP:{server_name}",
                    enabled=True,
                    command_count=1,
                    id_str=f"mcp-{server_name}-{tool.name}",
                )
                await tools_list.append(card)
                self.all_items.append({"type": "mcp", "name": f"{server_name}/{tool.name}", "card": card})
                self.selected_items.add(f"mcp-{server_name}-{tool.name}")

        self.category_counts["mcp"] = len(mcp_tools)

        # Update counts
        self._update_counts()

    def _update_counts(self) -> None:
        selected = len(self.selected_items)
        total = len(self.all_items)
        selected_label = self.query_one("#selected-count", Label)
        total_label = self.query_one("#total-count", Label)
        selected_label.update(f"Selected: {selected}")
        total_label.update(f"Total: {total}")

    @on(ListItem.highlighted)
    def on_item_highlighted(self, event: ListView.Highlighted) -> None:
        """Show tooltip/description on hover."""
        item = event.item
        if hasattr(item, "name"):
            desc = item.description if hasattr(item, "description") else ""
            self.app.notify(f"{item.name}: {desc[:60]}")

    async def action_save(self) -> None:
        """Save selected skills and start JARVIS."""
        # Build the new enabled list
        new_enabled = set()
        for item in self.all_items:
            card_id = item["id_str"]
            if card_id in self.selected_items:
                new_enabled.add(item["name"])

        # Update settings
        self.settings.skills.enabled = list(new_enabled)

        # Save config
        from jarvis.config.settings import save_settings
        save_settings(self.settings)

        self.app.notify(f"✅ Saved {len(new_enabled)} skills/tools! Starting JARVIS...", title="Setup Complete")
        await self.app.switch_screen("chat")

    async def action_select_all(self) -> None:
        """Select all items."""
        for item in self.all_items:
            self.selected_items.add(item["id_str"])
            item["card"].enabled = True
            # Update the card display
            await self._refresh_list(item["type"])
        self._update_counts()

    async def action_deselect_all(self) -> None:
        """Deselect all items."""
        self.selected_items.clear()
        for item in self.all_items:
            item["card"].enabled = False
            await self._refresh_list(item["type"])
        self._update_counts()

    async def action_toggle_selected(self) -> None:
        """Toggle the currently highlighted item."""
        list_view = self.query_one("#builtin-skills-list", ListView)
        if list_view.highlighted:
            item = list_view.highlighted
            card_id = item.id if hasattr(item, "id") else ""
            if card_id in self.selected_items:
                self.selected_items.discard(card_id)
            else:
                self.selected_items.add(card_id)
            # Refresh to show visual change
            await self._refresh_all()
            self._update_counts()

    async def _refresh_list(self, skill_type: str) -> None:
        """Refresh a specific list view."""
        list_id = f"{skill_type}-skills-list" if skill_type != "mcp" else "mcp-tools-list"
        try:
            lv = self.query_one(f"#{list_id}", ListView)
            await lv.refresh()
        except Exception:
            pass

    async def _refresh_all(self) -> None:
        """Refresh all lists."""
        for list_id in ["builtin-skills-list", "external-skills-list", "mcp-tools-list"]:
            try:
                lv = self.query_one(f"#{list_id}", ListView)
                await lv.refresh()
            except Exception:
                pass

    async def action_back(self) -> None:
        """Go back to chat screen."""
        await self.app.switch_screen("chat")


async def main():
    from jarvis.config.settings import load_settings
    from jarvis.agent.loop import AgentLoop
    from jarvis.skills.registry import SkillRegistry
    from jarvis.mcp.client import MCPClient

    settings = load_settings()
    registry = SkillRegistry(settings)
    await registry.initialize()
    loop = AgentLoop(settings, skill_registry=registry)
    await loop.initialize()

    from textual.app import App
    app = App()
    screen = SetupScreen(settings, registry, loop.mcp, loop)
    app.screen = screen
    await app.run_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
