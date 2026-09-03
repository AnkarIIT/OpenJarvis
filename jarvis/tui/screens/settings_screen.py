from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Button, Input, Select, Switch, Label
from textual.reactive import reactive

from jarvis.config.settings import Settings, save_settings


class SettingsScreen(Screen):
    BINDINGS = [
        ("escape", "back", "Back"),
        ("ctrl+s", "save", "Save"),
    ]

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.original_settings = settings.model_copy(deep=True)

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static("Settings", id="settings-title"),
                Static("LLM Configuration", classes="section-title"),
                Horizontal(
                    Label("Provider:"),
                    Select(
                        [("Ollama", "ollama"), ("Llama.cpp", "llama_cpp"), ("OpenAI", "openai"), ("Anthropic", "anthropic")],
                        value=self.settings.llm.provider,
                        id="llm-provider",
                    ),
                    id="provider-row",
                ),
                Horizontal(
                    Label("Model:"),
                    Input(value=self.settings.llm.model, id="llm-model"),
                    id="model-row",
                ),
                Horizontal(
                    Label("Base URL:"),
                    Input(value=self.settings.llm.base_url, id="llm-base-url"),
                    id="base-url-row",
                ),
                Horizontal(
                    Label("Temperature:"),
                    Input(value=str(self.settings.llm.temperature), id="llm-temperature"),
                    id="temp-row",
                ),
                Static("Voice Configuration", classes="section-title"),
                Horizontal(
                    Label("Enabled:"),
                    Switch(value=self.settings.voice.enabled, id="voice-enabled"),
                    id="voice-enabled-row",
                ),
                Horizontal(
                    Label("Wake Word:"),
                    Switch(value=self.settings.voice.wake_word_enabled, id="wake-word-enabled"),
                    id="wake-word-row",
                ),
                Static("UI Configuration", classes="section-title"),
                Horizontal(
                    Label("Theme:"),
                    Select([("JARVIS", "jarvis"), ("Dark", "dark"), ("Light", "light")], value=self.settings.ui.theme, id="ui-theme"),
                    id="theme-row",
                ),
                Horizontal(
                    Label("Stream:"),
                    Switch(value=self.settings.ui.stream, id="ui-stream"),
                    id="stream-row",
                ),
                Horizontal(
                    Button("Save", id="save-btn", variant="primary"),
                    Button("Reset", id="reset-btn"),
                    Button("Cancel", id="cancel-btn", variant="error"),
                    id="settings-actions",
                ),
                id="settings-container",
            )
        )

    def action_back(self) -> None:
        self.app.switch_screen("chat")

    def action_save(self) -> None:
        self._save_settings()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save_settings()
        elif event.button.id == "reset-btn":
            self._reset_settings()
        elif event.button.id == "cancel-btn":
            self.action_back()

    def _save_settings(self) -> None:
        self.settings.llm.provider = self.query_one("#llm-provider", Select).value
        self.settings.llm.model = self.query_one("#llm-model", Input).value
        self.settings.llm.base_url = self.query_one("#llm-base-url", Input).value
        self.settings.llm.temperature = float(self.query_one("#llm-temperature", Input).value or 0.7)
        self.settings.voice.enabled = self.query_one("#voice-enabled", Switch).value
        self.settings.voice.wake_word_enabled = self.query_one("#wake-word-enabled", Switch).value
        self.settings.ui.theme = self.query_one("#ui-theme", Select).value
        self.settings.ui.stream = self.query_one("#ui-stream", Switch).value

        save_settings(self.settings)
        self.app.notify("Settings saved")

    def _reset_settings(self) -> None:
        self.query_one("#llm-provider", Select).value = self.original_settings.llm.provider
        self.query_one("#llm-model", Input).value = self.original_settings.llm.model
        self.query_one("#llm-base-url", Input).value = self.original_settings.llm.base_url
        self.query_one("#llm-temperature", Input).value = str(self.original_settings.llm.temperature)
        self.query_one("#voice-enabled", Switch).value = self.original_settings.voice.enabled
        self.query_one("#wake-word-enabled", Switch).value = self.original_settings.voice.wake_word_enabled
        self.query_one("#ui-theme", Select).value = self.original_settings.ui.theme
        self.query_one("#ui-stream", Switch).value = self.original_settings.ui.stream