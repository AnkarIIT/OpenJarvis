from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static
from textual.reactive import reactive

from jarvis.config.settings import Settings


class StatusBar(Static):
    current_screen = reactive("chat")
    llm_status = reactive("connected")
    voice_status = reactive(False)
    token_count = reactive(0)

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings

    def compose(self) -> ComposeResult:
        yield Static("", id="status-left")
        yield Static("", id="status-center")
        yield Static("", id="status-right")

    def watch_current_screen(self, screen: str) -> None:
        self.update_display()

    def watch_llm_status(self, status: str) -> None:
        self.update_display()

    def watch_voice_status(self, listening: bool) -> None:
        self.update_display()

    def watch_token_count(self, count: int) -> None:
        self.update_display()

    def update_display(self) -> None:
        left = self.query_one("#status-left", Static)
        center = self.query_one("#status-center", Static)
        right = self.query_one("#status-right", Static)

        screen_icons = {
            "chat": "💬",
            "skills": "🛠️",
            "memory": "🧠",
            "tools": "🔧",
            "settings": "⚙️",
            "voice": "🎤",
        }

        left.update(f"{screen_icons.get(self.current_screen, '📱')} {self.current_screen.title()}")

        llm_icon = "🟢" if self.llm_status == "connected" else "🔴"
        voice_icon = "🎤" if self.voice_status else "🔇"
        center.update(f"{llm_icon} {self.settings.llm.model} | {voice_icon}")

        right.update(f"Tokens: {self.token_count}")

    def update_screen(self, screen: str) -> None:
        self.current_screen = screen

    def update_voice_status(self, listening: bool) -> None:
        self.voice_status = listening

    def update_llm_status(self, status: str) -> None:
        self.llm_status = status

    def update_tokens(self, count: int) -> None:
        self.token_count = count