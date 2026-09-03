from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, ProgressBar, Static
from textual.reactive import reactive

from jarvis.config.installer import Installer
from jarvis.config.settings import Settings


class SetupScreen(Screen):
    BINDINGS = [("escape", "cancel", "Cancel")]

    progress_text = reactive("Initializing...")
    progress_value = reactive(0.0)

    def __init__(self, settings: Settings | None = None):
        super().__init__()
        self.settings = settings
        self.installer = Installer(settings)
        self.install_task = None

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static("🤖 JARVIS", id="setup-logo"),
                Static("Just A Rather Very Intelligent System", id="setup-tagline"),
                Static("", id="setup-status"),
                ProgressBar(total=100, show_eta=False, id="setup-progress"),
                Static("", id="setup-detail"),
                Button("Cancel", id="cancel-btn", variant="error"),
                id="setup-container",
            )
        )

    async def on_mount(self) -> None:
        self.install_task = self.run_worker(self._run_install, exclusive=True)

    async def _run_install(self) -> None:
        try:
            self.update_progress(5, "Checking prerequisites...")
            await self.installer._check_prerequisites()

            self.update_progress(15, "Detecting local AI...")
            await self.installer._detect_and_install_ai()

            self.update_progress(60, "Downloading voice models...")
            await self.installer._download_voice_models()

            self.update_progress(80, "Setting up MCP servers...")
            await self.installer._setup_mcp_servers()

            self.update_progress(90, "Creating configuration...")
            self.installer._create_config()

            self.update_progress(95, "Adding to PATH...")
            self.installer._add_to_path()

            self.update_progress(100, "Setup complete!")

            self.app.call_later(self._launch_main)
        except Exception as e:
            self.query_one("#setup-status", Static).update(f"[red]Error: {e}[/red]")
            self.query_one("#setup-detail", Static).update("Check logs for details")

    def update_progress(self, value: float, text: str) -> None:
        self.progress_value = value
        self.progress_text = text
        progress_bar = self.query_one("#setup-progress", ProgressBar)
        progress_bar.progress = value
        self.query_one("#setup-status", Static).update(text)
        self.query_one("#setup-detail", Static).update(f"{value:.0f}% complete")

    def _launch_main(self) -> None:
        self.app.switch_screen("chat")

    def action_cancel(self) -> None:
        if self.install_task:
            self.install_task.cancel()
        self.app.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.action_cancel()