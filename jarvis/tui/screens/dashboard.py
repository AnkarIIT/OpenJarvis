from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Label, ListView, ListItem, TabbedContent, TabPane
from textual.reactive import reactive
from textual import on

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillRegistry
from jarvis.mcp.client import MCPClient, MCPTool
from jarvis.agent.loop import AgentLoop
from jarvis.utils.logger import get_logger

logger = get_logger(__name__)


class JarvisDashboardScreen(Screen):
    BINDINGS = [
        ("escape", "back", "Back"),
        ("ctrl+k", "command_palette", "Commands"),
        ("ctrl+1", "switch_tab", "Chat"),
        ("ctrl+2", "switch_tab", "Skills"),
        ("ctrl+3", "switch_tab", "Memory"),
        ("ctrl+4", "switch_tab", "Tools"),
        ("ctrl+5", "switch_tab", "Voice"),
        ("ctrl+6", "switch_tab", "Settings"),
        ("ctrl+7", "switch_tab", "Dashboard"),
    ]

    def __init__(self, settings: Settings, agent_loop: AgentLoop, skill_registry: SkillRegistry):
        super().__init__()
        self.settings = settings
        self.agent_loop = agent_loop
        self.skill_registry = skill_registry
        self.mcp_client = agent_loop.mcp

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static("JARVIS", id="dash-logo"),
                Static("Just A Rather Very Intelligent System", id="dash-tagline"),
                Static("Keyboard shortcuts", id="dash-help"),
                TabbedContent(id="dash-tabs"),
                Horizontal(Label(" "), Label(""), id="dash-status-bar"),
            ),
            id="dash-container",
        )

    async def on_mount(self) -> None:
        await self.mcp_client.connect_all()

        tabs = self.query_one("#dash-tabs", TabbedContent)

        builtin_pane = self._build_skills_tab("builtin", "Built-in Skills")
        tabs.add_child(builtin_pane)

        external_pane = self._build_skills_tab("external", "External Skills")
        tabs.add_child(external_pane)

        mcp_pane = self._build_tools_tab()
        tabs.add_child(mcp_pane)

        voice_pane = self._build_voice_tab()
        tabs.add_child(voice_pane)

        status_pane = self._build_status_tab()
        tabs.add_child(status_pane)

        self._update_status_bar()

    def _build_skills_tab(self, skill_type: str, title: str) -> TabPane:
        if skill_type == "builtin":
            skills = [
                ("system_monitor", "6", "CPU, memory, disk, GPU, processes"),
                ("code_assistant", "3", "AST analysis, find TODOs, list functions"),
                ("memory", "3", "Remember, recall, forget via ChromaDB"),
                ("browser", "9", "Navigate, click, type, screenshot, scroll"),
                ("voice_control", "4", "Voice on/off, test, language setting"),
            ]
        else:
            skills = [
                ("marketing", "3", "Marketing playbooks, copywriting, ads"),
                ("visualizer", "6", "AI visualizer faces, animations"),
                ("memory_vault", "6", "Persistent key-value memory vault"),
                ("barehands", "6", "Air-board hand tracking, cards"),
                ("backtalk", "6", "Mood-based conversational AI"),
                ("fullstack_agent", "4", "Full-stack development toolbox"),
            ]

        list_items = []
        for name, count, desc in skills:
            list_items.append(
                ListItem(
                    Horizontal(
                        Label(f"⚡ {name}", classes="skill-name"),
                        Label(f"[{count}]", classes="skill-count"),
                        Label(desc, classes="skill-desc"),
                        classes="skill-item",
                    ),
                    id=f"skill-{name}",
                )
            )

        return TabPane(
            Container(
                Vertical(
                    Static(title, classes="section-title"),
                    ListView(*list_items, id=f"skills-list-{skill_type}"),
                ),
                id=f"skills-pane-{skill_type}",
            ),
            title=title,
            id=f"tab-{skill_type}",
        )

    def _build_tools_tab(self) -> TabbedContent:
        tools_by_server: dict[str, list[MCPTool]] = {}
        for tool in self.mcp_client.tools:
            server = tool.server_name
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append(tool)

        tabs = TabbedContent(id="tools-tabs")

        for server_name, tools in tools_by_server.items():
            list_items = []
            for tool in tools:
                list_items.append(
                    ListItem(
                        Horizontal(
                            Label(f"🔧 {tool.name}", classes="tool-name"),
                            Label(tool.description[:60], classes="tool-desc"),
                            classes="tool-item",
                        ),
                        id=f"tool-{tool.name}",
                    )
                )

            tabs.add_child(
                TabPane(
                    Container(
                        Vertical(
                            Static(f"🔧 {server_name.upper()} MCP Server", classes="section-title"),
                            ListView(*list_items, id=f"tools-list-{server_name}"),
                        ),
                        id=f"tools-pane-{server_name}",
                    ),
                    title=server_name.capitalize(),
                    id=f"tab-{server_name}",
                )
            )

        return tabs

    def _build_voice_tab(self) -> TabPane:
        return TabPane(
            Container(
                Vertical(
                    Static("🎤 Voice Configuration", classes="section-title"),
                    Label("Wake Word: openWakeWord (no API key needed)", classes="voice-item"),
                    Label("STT: Vosk / Whisper.cpp", classes="voice-item"),
                    Label("TTS: Piper TTS (auto-download)", classes="voice-item"),
                    Label("Wake: Hey JARVIS", classes="voice-item"),
                    Label("Language: Auto-detect", classes="voice-item"),
                    Label("Sarvam AI: Cloud backup", classes="voice-item"),
                    Label("Voice Mode: Ctrl+V / Space to toggle", classes="voice-item"),
                    Label("Full offline: no API needed", classes="voice-item"),
                ),
                id="voice-pane",
            ),
            title="Voice",
            id="tab-voice",
        )

    def _build_status_tab(self) -> TabPane:
        from jarvis.utils.detectors import detect_all_local_ai, get_system_info

        ai_status = detect_all_local_ai()
        sys_info = get_system_info()

        rows = []
        for provider, info in ai_status.items():
            status = "OK" if info["available"] else "MISSING"
            models = ", ".join(info.get("models", []))[:40]
            rows.append(
                ListItem(
                    Horizontal(
                        Label(f"{status} {provider.title()}", classes="status-item"),
                        Label(f"{models}", classes="status-desc"),
                        classes="status-item",
                    ),
                    id=f"status-{provider}",
                )
            )

        return TabPane(
            Container(
                Vertical(
                    Static("System Status", classes="section-title"),
                    Label(f"Platform: {sys_info['platform']}", classes="status-item"),
                    Label(f"Python: {sys_info['python_version'].split()[0]}", classes="status-item"),
                    Label(f"CPU: {sys_info['cpu_count']} cores | RAM: {sys_info['memory_total'] // (1024**3)} GB", classes="status-item"),
                    Static("", classes="status-separator"),
                    Static("Local AI Providers", classes="section-title"),
                    ListView(*rows, id="status-ai-list"),
                ),
                id="status-pane",
            ),
            title="Status",
            id="tab-status",
        )

    def _update_status_bar(self) -> None:
        left = self.query_one("#dash-status-left", Label)
        center = self.query_one("#dash-status-center", Label)
        right = self.query_one("#dash-status-right", Label)

        model = self.settings.llm.model
        provider = self.settings.llm.provider
        mcp_count = len(self.mcp_client.tools)
        skill_count = len(self.skill_registry.list_commands())

        left.update(f"JARVIS | {skill_count} cmds | {mcp_count} tools")
        center.update(f"{model} ({provider})")
        right.update("Ctrl+1-7 | Ctrl+K")

    @on(ListItem.Highlighted)
    def on_skill_highlighted(self, event: ListView.Highlighted) -> None:
        item = event.item
        if item and item.id:
            skill_id = item.id.replace("skill-", "").replace("tool-", "")
            self.app.notify(f"Selected: {skill_id}", title="JARVIS")

    async def action_back(self) -> None:
        await self.app.switch_screen("chat")

    def action_switch_tab(self, tab: str) -> None:
        tab_map = {
            "Chat": "chat",
            "Skills": "skills",
            "Memory": "memory",
            "Tools": "tools",
            "Voice": "voice",
            "Settings": "settings",
            "Dashboard": "dashboard",
        }
        target = tab_map.get(tab)
        if target and target != "chat":
            self.app.notify(f"Switching to {tab}", title="JARVIS")
            self.app.switch_screen(target)


async def main():
    from jarvis.config.settings import load_settings
    from jarvis.agent.loop import AgentLoop
    from jarvis.skills.registry import SkillRegistry

    settings = load_settings()
    registry = SkillRegistry(settings)
    await registry.initialize()
    loop = AgentLoop(settings, skill_registry=registry)
    await loop.initialize()

    from textual.app import App
    app = App()
    screen = JarvisDashboardScreen(settings, loop, registry)
    app.screen = screen
    await app.run_async()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
