from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.screen import Screen
from textual.widgets import Static, Button, Input, ListView, ListItem, Label
from textual.reactive import reactive

from jarvis.config.settings import Settings
from jarvis.memory.vector_store import VectorStore


class MemoryScreen(Screen):
    BINDINGS = [
        ("escape", "back", "Back"),
        ("/", "search", "Search"),
    ]

    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.vector_store = VectorStore(settings) if settings.memory.enabled else None
        self.memories = []

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static("Memory & Knowledge", id="memory-title"),
                Horizontal(
                    Input(placeholder="Search memories...", id="memory-search"),
                    Button("Refresh", id="refresh-btn"),
                    Button("Add Memory", id="add-btn", variant="primary"),
                    id="memory-actions",
                ),
                ListView(id="memory-list"),
                id="memory-container",
            )
        )

    async def on_mount(self) -> None:
        if self.vector_store:
            await self._load_memories()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-btn":
            await self._load_memories()
        elif event.button.id == "add-btn":
            await self._add_memory_dialog()

    async def _add_memory_dialog(self) -> None:
        """Open a simple prompt to add a memory entry."""
        from textual import work
        # Show an input modal for adding memory
        prompt = self.query_one("#memory-search", Input)
        content = prompt.value.strip()
        if not content:
            self.app.notify("Enter text in the search box, then click 'Add Memory'", title="Add Memory")
            return
        if not self.vector_store:
            self.app.notify("Vector store not available", title="Error")
            return
        try:
            await self.vector_store.add_memory(content)
            await self._load_memories()
            self.app.notify(f"Memory added: {content[:40]}...", title="Success")
        except Exception as e:
            self.app.notify(f"Failed to add memory: {e}", title="Error")

    async def _load_memories(self) -> None:
        self.memories = await self.vector_store.list_memories()

        list_view = self.query_one("#memory-list", ListView)
        await list_view.clear()

        for memory in self.memories:
            item = ListItem(
                Horizontal(
                    Label(f"🧠 {memory['content'][:80]}...", classes="memory-content"),
                    Label(f"{memory['timestamp']}", classes="memory-time"),
                    classes="memory-item",
                ),
                id=f"memory-{memory['id']}",
            )
            await list_view.append(item)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value.strip() and self.vector_store:
            results = await self.vector_store.search(event.value.strip())
            list_view = self.query_one("#memory-list", ListView)
            await list_view.clear()

            for memory in results:
                item = ListItem(
                    Horizontal(
                        Label(f"🧠 {memory['content'][:80]}...", classes="memory-content"),
                        Label(f"{memory['timestamp']} (score: {memory['score']:.2f})", classes="memory-time"),
                        classes="memory-item",
                    ),
                    id=f"memory-{memory['id']}",
                )
                await list_view.append(item)

    async def action_back(self) -> None:
        await self.app.switch_screen("chat")

    async def action_search(self) -> None:
        self.query_one("#memory-search", Input).focus()