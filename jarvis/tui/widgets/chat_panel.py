from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, RichLog, Label
from textual.reactive import reactive

from jarvis.agent.loop import AgentLoop
from jarvis.config.settings import Settings


class ChatPanel(Static):
    def __init__(self, agent_loop: AgentLoop, settings: Settings):
        super().__init__()
        self.agent_loop = agent_loop
        self.settings = settings
        self.messages = []
        self.streaming = False
        self.current_message = ""

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(
            RichLog(id="chat-log", highlight=True, markup=True),
            id="chat-scroll",
        )

    async def add_user_message(self, message: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold cyan]You:[/bold cyan] {message}")
        self.messages.append({"role": "user", "content": message})

    async def stream_assistant_message(self, chunk: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        if not self.streaming:
            log.write("[bold green]JARVIS:[/bold green] ")
            self.streaming = True
        log.write(chunk, end="")
        self.current_message += chunk

    async def finish_streaming(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        if self.streaming:
            log.write("")
            self.messages.append({"role": "assistant", "content": self.current_message})
            self.current_message = ""
            self.streaming = False

        scroll = self.query_one("#chat-scroll", ScrollableContainer)
        scroll.scroll_end(animate=False)

    def clear(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        self.messages = []
        self.current_message = ""
        self.streaming = False