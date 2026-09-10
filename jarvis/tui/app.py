from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static

from jarvis.config.settings import Settings, load_settings
from jarvis.skills.registry import SkillRegistry
from jarvis.tui.screens.chat import ChatScreen
from jarvis.tui.screens.skills import SkillsScreen
from jarvis.tui.screens.tools import ToolsScreen
from jarvis.tui.screens.memory import MemoryScreen
from jarvis.tui.screens.settings_screen import SettingsScreen
from jarvis.tui.screens.setup_screen import SetupScreen
from jarvis.tui.screens.voice import VoiceScreen
from jarvis.tui.widgets.chat_panel import ChatPanel
from jarvis.tui.widgets.status_bar import StatusBar
from jarvis.tui.widgets.command_palette import CommandPalette
from jarvis.agent.loop import AgentLoop
from jarvis.voice.pipeline import VoicePipeline


class JarvisApp(App):
    TITLE = "JARVIS"
    SUB_TITLE = "Just A Rather Very Intelligent System"

    CSS_PATH = "css/jarvis.tcss"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+c", "clear_chat", "Clear Chat"),
        Binding("ctrl+s", "toggle_sidebar", "Sidebar"),
        Binding("ctrl+k", "command_palette", "Commands"),
        Binding("ctrl+v", "toggle_voice", "Voice"),
        Binding("f1", "help", "Help"),
        Binding("ctrl+t", "switch_tab('chat')", "Chat"),
        Binding("ctrl+g", "switch_tab('skills')", "Skills"),
        Binding("ctrl+m", "switch_tab('memory')", "Memory"),
        Binding("ctrl+o", "switch_tab('tools')", "Tools"),
        Binding("ctrl+y", "switch_tab('settings')", "Settings"),
        Binding("ctrl+u", "switch_tab('voice')", "Voice"),
        Binding("ctrl+b", "setup", "Setup"),
    ]

    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self.settings = settings or load_settings()
        self.skill_registry = SkillRegistry(self.settings)
        self.agent_loop = AgentLoop(self.settings, skill_registry=self.skill_registry)
        self.voice_pipeline = VoicePipeline(self.settings, self.agent_loop) if self.settings.voice.enabled else None
        self.current_screen = "chat"
        self.chat_panel: ChatPanel | None = None
        self.status_bar: StatusBar | None = None
        self.command_palette: CommandPalette | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Horizontal(
                Vertical(
                    Static("JARVIS", id="logo"),
                    Static("Just A Rather Very Intelligent System", id="tagline"),
                    id="sidebar",
                ),
                Vertical(
                    Container(id="main-content"),
                    id="content-area",
                ),
            ),
            id="app-container",
        )
        yield Footer()
        yield StatusBar(self.settings, id="status-bar")
        yield CommandPalette(id="command-palette")

    async def on_mount(self) -> None:
        self.status_bar = self.query_one("#status-bar", StatusBar)
        self.command_palette = self.query_one("#command-palette", CommandPalette)

        await self.agent_loop.initialize()

        if self.voice_pipeline and hasattr(self.skill_registry, "skill_instances"):
            voice_skill = self.skill_registry.skill_instances.get("voice_control")
            if voice_skill and hasattr(voice_skill, "set_voice_pipeline"):
                voice_skill.set_voice_pipeline(self.voice_pipeline)

        await self.switch_screen("chat")

        if self.voice_pipeline and self.settings.voice.wake_word_enabled:
            await self.voice_pipeline.start_wake_word_listener()

    async def switch_screen(self, screen_name: str) -> None:
        main_content = self.query_one("#main-content", Container)
        await main_content.remove_children()

        screen_map = {
            "chat": ChatScreen(self.agent_loop, self.settings),
            "skills": SkillsScreen(self.settings, self.skill_registry),
            "memory": MemoryScreen(self.settings),
            "tools": ToolsScreen(self.settings, mcp_client=self.agent_loop.mcp),
            "settings": SettingsScreen(self.settings),
            "setup": SetupScreen(self.settings, self.skill_registry, self.agent_loop.mcp, self.agent_loop),
            "voice": VoiceScreen(self.voice_pipeline, self.settings) if self.voice_pipeline else None,
        }

        screen = screen_map.get(screen_name)
        if screen is None and screen_name == "voice":
            self.app.notify("Voice is not enabled in settings", title="JARVIS")
            return
        if screen is None and screen_name == "setup":
            self.app.notify("Setup screen", title="JARVIS")
            return
        if screen:
            self.current_screen = screen_name
            await main_content.mount(screen)
            self.status_bar.update_screen(screen_name)
            if screen_name == "chat":
                try:
                    self.chat_panel = (
                        self.query_one("#chat-messages", Container)
                        .query_one(ChatPanel, see_type=False)
                    )
                except Exception:
                    self.chat_panel = None

    def action_switch_tab(self, screen_name: str) -> None:
        self.run_worker(self.switch_screen(screen_name))

    def action_setup(self) -> None:
        """Open the Feynman-style setup screen."""
        self.run_worker(self.switch_screen("setup"))

    def action_clear_chat(self) -> None:
        if self.current_screen == "chat" and self.chat_panel:
            self.chat_panel.clear()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar")
        sidebar.display = not sidebar.display

    def action_command_palette(self) -> None:
        if self.command_palette:
            self.command_palette.toggle()

    def action_toggle_voice(self) -> None:
        if self.voice_pipeline:
            self.voice_pipeline.toggle_listening()
            self.status_bar.update_voice_status(self.voice_pipeline.is_listening)

    def action_help(self) -> None:
        self.command_palette.show_help()

    async def on_unmount(self) -> None:
        if self.voice_pipeline:
            await self.voice_pipeline.stop()

        for skill in self.skill_registry.skill_instances.values():
            if hasattr(skill, "_stop") and callable(skill._stop):
                try:
                    await skill._stop()
                except Exception as e:
                    print(f"Failed to stop skill {getattr(skill, 'name', 'unknown')}: {e}")


def main() -> None:
    app = JarvisApp()
    app.run()


if __name__ == "__main__":
    main()
