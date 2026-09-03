from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Input, Static, Button
from textual.reactive import reactive

from jarvis.agent.loop import AgentLoop
from jarvis.config.settings import Settings
from jarvis.tui.widgets.chat_panel import ChatPanel


class ChatScreen(Screen):
    BINDINGS = [
        ("escape", "focus_input", "Focus Input"),
        ("ctrl+l", "clear", "Clear"),
    ]

    def __init__(self, agent_loop: AgentLoop, settings: Settings):
        super().__init__()
        self.agent_loop = agent_loop
        self.settings = settings
        self.chat_panel: ChatPanel | None = None

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Container(id="chat-messages"),
                Horizontal(
                    Input(placeholder="Message JARVIS...", id="chat-input"),
                    Button("Send", id="send-btn", variant="primary"),
                    id="input-container",
                ),
                id="chat-container",
            )
        )

    async def on_mount(self) -> None:
        self.chat_panel = ChatPanel(self.agent_loop, self.settings)
        messages_container = self.query_one("#chat-messages", Container)
        await messages_container.mount(self.chat_panel)

        input_widget = self.query_one("#chat-input", Input)
        input_widget.focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip():
            await self._send_message(event.value.strip())
            event.input.value = ""

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            input_widget = self.query_one("#chat-input", Input)
            if input_widget.value.strip():
                await self._send_message(input_widget.value.strip())
                input_widget.value = ""

    async def _send_message(self, message: str) -> None:
        if self.chat_panel:
            await self.chat_panel.add_user_message(message)
            async for chunk in self.agent_loop.run(message):
                await self.chat_panel.stream_assistant_message(chunk)
            await self.chat_panel.finish_streaming()

    def action_focus_input(self) -> None:
        self.query_one("#chat-input", Input).focus()

    def action_clear(self) -> None:
        if self.chat_panel:
            self.chat_panel.clear()