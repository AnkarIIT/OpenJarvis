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
                    Label("TTS Engine:"),
                    Select(
                        [("Piper", "piper"), ("Sarvam AI", "sarvam")],
                        value=self.settings.voice.tts_engine,
                        id="tts-engine",
                    ),
                    id="tts-engine-row",
                ),
                Horizontal(
                    Label("STT Engine:"),
                    Select(
                        [("Vosk", "vosk"), ("Sarvam AI", "sarvam")],
                        value=self.settings.voice.stt_engine,
                        id="stt-engine",
                    ),
                    id="stt-engine-row",
                ),
                Horizontal(
                    Label("Sarvam API Key:"),
                    Input(value=self.settings.voice.sarvam_api_key or "", id="sarvam-api-key", password=True),
                    id="sarvam-api-key-row",
                ),
                Horizontal(
                    Label("TTS Speaker:"),
                    Select(
                        [("meera (female)", "meera"), ("pramod (male)", "pramod"), ("shubh (male)", "shubh"), ("shubhangi (female)", "shubhangi")],
                        value=self.settings.voice.sarvam_tts_speaker,
                        id="sarvam-tts-speaker",
                    ),
                    id="sarvam-tts-speaker-row",
                ),
                Horizontal(
                    Label("TTS Pace:"),
                    Input(value=str(self.settings.voice.sarvam_tts_pace), id="sarvam-tts-pace"),
                    id="sarvam-tts-pace-row",
                ),
                Horizontal(
                    Label("TTS Temperature:"),
                    Input(value=str(self.settings.voice.sarvam_tts_temperature), id="sarvam-tts-temperature"),
                    id="sarvam-tts-temperature-row",
                ),
                Horizontal(
                    Label("STT Model:"),
                    Select(
                        [("Saaras v3", "saaras:v3"), ("Saaras v4", "saaras:v4")],
                        value=self.settings.voice.sarvam_stt_model,
                        id="sarvam-stt-model",
                    ),
                    id="sarvam-stt-model-row",
                ),
                Horizontal(
                    Label("Response Language:"),
                    Select(
                        [("English (en-IN)", "en-IN"), ("Hindi (hi-IN)", "hi-IN"), ("Tamil (ta-IN)", "ta-IN"), ("Telugu (te-IN)", "te-IN"), ("Bengali (bn-IN)", "bn-IN"), ("Marathi (mr-IN)", "mr-IN"), ("Gujarati (gu-IN)", "gu-IN"), ("Malayalam (ml-IN)", "ml-IN"), ("Punjabi (pa-IN)", "pa-IN"), ("Kannada (kn-IN)", "kn-IN"), ("Urdu (ur-IN)", "ur-IN"), ("Auto-Detect", "unknown")],
                        value=self.settings.voice.language,
                        id="voice-language",
                    ),
                    id="voice-language-row",
                ),
                Horizontal(
                    Label("Auto-Detect Language:"),
                    Switch(value=self.settings.voice.language_detection, id="lang-detection"),
                    id="lang-detection-row",
                ),
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

    async def action_back(self) -> None:
        await self.app.switch_screen("chat")

    def action_save(self) -> None:
        self._save_settings()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-btn":
            self._save_settings()
        elif event.button.id == "reset-btn":
            self._reset_settings()
        elif event.button.id == "cancel-btn":
            await self.action_back()

    def _save_settings(self) -> None:
        self.settings.llm.provider = self.query_one("#llm-provider", Select).value
        self.settings.llm.model = self.query_one("#llm-model", Input).value
        self.settings.llm.base_url = self.query_one("#llm-base-url", Input).value
        self.settings.llm.temperature = float(self.query_one("#llm-temperature", Input).value or 0.7)
        self.settings.voice.tts_engine = self.query_one("#tts-engine", Select).value
        self.settings.voice.stt_engine = self.query_one("#stt-engine", Select).value
        self.settings.voice.sarvam_api_key = self.query_one("#sarvam-api-key", Input).value
        self.settings.voice.language = self.query_one("#voice-language", Select).value
        self.settings.voice.language_detection = self.query_one("#lang-detection", Switch).value
        self.settings.voice.enabled = self.query_one("#voice-enabled", Switch).value
        self.settings.voice.wake_word_enabled = self.query_one("#wake-word-enabled", Switch).value
        self.settings.voice.sarvam_tts_speaker = self.query_one("#sarvam-tts-speaker", Select).value
        self.settings.voice.sarvam_tts_pace = float(self.query_one("#sarvam-tts-pace", Input).value or 1.0)
        self.settings.voice.sarvam_tts_temperature = float(self.query_one("#sarvam-tts-temperature", Input).value or 0.6)
        self.settings.voice.sarvam_stt_model = self.query_one("#sarvam-stt-model", Select).value
        self.settings.ui.theme = self.query_one("#ui-theme", Select).value
        self.settings.ui.stream = self.query_one("#ui-stream", Switch).value

        save_settings(self.settings)
        self.app.notify("Settings saved")

    def _reset_settings(self) -> None:
        self.query_one("#llm-provider", Select).value = self.original_settings.llm.provider
        self.query_one("#llm-model", Input).value = self.original_settings.llm.model
        self.query_one("#llm-base-url", Input).value = self.original_settings.llm.base_url
        self.query_one("#llm-temperature", Input).value = str(self.original_settings.llm.temperature)
        self.query_one("#tts-engine", Select).value = self.original_settings.voice.tts_engine
        self.query_one("#stt-engine", Select).value = self.original_settings.voice.stt_engine
        self.query_one("#sarvam-api-key", Input).value = self.original_settings.voice.sarvam_api_key or ""
        self.query_one("#voice-language", Select).value = self.original_settings.voice.language
        self.query_one("#lang-detection", Switch).value = self.original_settings.voice.language_detection
        self.query_one("#voice-enabled", Switch).value = self.original_settings.voice.enabled
        self.query_one("#wake-word-enabled", Switch).value = self.original_settings.voice.wake_word_enabled
        self.query_one("#sarvam-tts-speaker", Select).value = self.original_settings.voice.sarvam_tts_speaker
        self.query_one("#sarvam-tts-pace", Input).value = str(self.original_settings.voice.sarvam_tts_pace)
        self.query_one("#sarvam-tts-temperature", Input).value = str(self.original_settings.voice.sarvam_tts_temperature)
        self.query_one("#sarvam-stt-model", Select).value = self.original_settings.voice.sarvam_stt_model
        self.query_one("#ui-theme", Select).value = self.original_settings.ui.theme
        self.query_one("#ui-stream", Switch).value = self.original_settings.ui.stream