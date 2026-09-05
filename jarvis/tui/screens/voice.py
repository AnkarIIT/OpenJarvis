from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Button, Switch, Label, ProgressBar
from textual.reactive import reactive

from jarvis.config.settings import Settings
from jarvis.voice.pipeline import VoicePipeline


class VoiceScreen(Screen):
    BINDINGS = [
        ("escape", "back", "Back"),
        ("space", "toggle_listening", "Toggle Listening"),
    ]

    def __init__(self, voice_pipeline: VoicePipeline | None, settings: Settings):
        super().__init__()
        self.voice_pipeline = voice_pipeline
        self.settings = settings
        self.is_listening = False

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static("Voice Control", id="voice-title"),
                Horizontal(
                    Label("Status:"),
                    Label("Idle", id="voice-status", classes="status-indicator"),
                    id="voice-status-row",
                ),
                Horizontal(
                    Label("Listening:"),
                    Switch(value=False, id="listening-switch"),
                    id="listening-row",
                ),
                Horizontal(
                    Label("Wake Word:"),
                    Switch(value=self.settings.voice.wake_word_enabled, id="wake-word-switch"),
                    id="wake-word-row",
                ),
                Horizontal(
                    Label("TTS Engine:"),
                    Label(self.settings.voice.tts_engine, id="tts-engine"),
                    id="tts-row",
                ),
                Horizontal(
                    Label("STT Engine:"),
                    Label(self.settings.voice.stt_engine, id="stt-engine"),
                    id="stt-row",
                ),
                Horizontal(
                    Label("Language:"),
                    Label(self.settings.voice.language, id="voice-language"),
                    id="language-row",
                ),
                ProgressBar(total=100, show_eta=False, id="voice-level"),
                Horizontal(
                    Button("Test TTS", id="test-tts-btn", variant="primary"),
                    Button("Test STT", id="test-stt-btn"),
                    Button("Calibrate", id="calibrate-btn"),
                    id="voice-actions",
                ),
                id="voice-container",
            )
        )

    def action_back(self) -> None:
        self.app.switch_screen("chat")

    def action_toggle_listening(self) -> None:
        if self.voice_pipeline:
            self.voice_pipeline.toggle_listening()
            self.is_listening = self.voice_pipeline.is_listening
            self.query_one("#listening-switch", Switch).value = self.is_listening
            self.query_one("#voice-status", Label).update("Listening" if self.is_listening else "Idle")

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        if event.switch.id == "listening-switch" and self.voice_pipeline:
            if event.value:
                await self.voice_pipeline.start_listening()
            else:
                await self.voice_pipeline.stop_listening()
            self.is_listening = event.value
            self.query_one("#voice-status", Label).update("Listening" if event.value else "Idle")

        elif event.switch.id == "wake-word-switch" and self.voice_pipeline:
            self.settings.voice.wake_word_enabled = event.value
            if event.value:
                await self.voice_pipeline.start_wake_word_listener()
            else:
                await self.voice_pipeline.stop_wake_word_listener()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "test-tts-btn" and self.voice_pipeline:
            await self.voice_pipeline.speak("Hello, I am JARVIS. Voice systems operational.")
        elif event.button.id == "test-stt-btn" and self.voice_pipeline:
            self.query_one("#voice-status", Label).update("Recording...")
            text = await self.voice_pipeline.listen_once()
            self.query_one("#voice-status", Label).update(f"Heard: {text}")
        elif event.button.id == "calibrate-btn" and self.voice_pipeline:
            await self.voice_pipeline.calibrate()