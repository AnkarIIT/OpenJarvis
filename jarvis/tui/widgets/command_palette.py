from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, Input, ListView, ListItem, Label
from textual.reactive import reactive


class CommandPalette(ModalScreen):
    BINDINGS = [
        ("escape", "close", "Close"),
        ("enter", "execute", "Execute"),
    ]

    visible = reactive(False)
    commands = reactive([])

    def __init__(self):
        super().__init__()
        self.commands = [
            ("/help", "Show help"),
            ("/clear", "Clear chat"),
            ("/model", "Switch model"),
            ("/skills", "Manage skills"),
            ("/tools", "Manage tools"),
            ("/memory", "View memory"),
            ("/settings", "Open settings"),
            ("/voice", "Voice settings"),
            ("/status", "System status"),
            ("/install", "Install skill"),
            ("/mcp", "MCP servers"),
            ("/exit", "Exit JARVIS"),
        ]

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static("Command Palette", id="palette-title"),
                Input(placeholder="Type command...", id="palette-input"),
                ListView(id="palette-list"),
                id="palette-container",
            )
        )

    def on_mount(self) -> None:
        self._update_list()
        self.display = False

    def _update_list(self) -> None:
        list_view = self.query_one("#palette-list", ListView)
        list_view.clear()

        for cmd, desc in self.commands:
            item = ListItem(
                Horizontal(
                    Label(cmd, classes="cmd-name"),
                    Label(desc, classes="cmd-desc"),
                ),
                id=f"cmd-{cmd[1:]}",
            )
            list_view.append(item)

    def toggle(self) -> None:
        self.visible = not self.visible
        self.display = self.visible
        if self.visible:
            self.query_one("#palette-input", Input).focus()
            self.query_one("#palette-input", Input).value = ""

    def show_help(self) -> None:
        self.toggle()

    async def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        if query.startswith("/"):
            filtered = [(c, d) for c, d in self.commands if query in c.lower()]
        else:
            filtered = [(c, d) for c, d in self.commands if query in c.lower() or query in d.lower()]

        list_view = self.query_one("#palette-list", ListView)
        list_view.clear()

        for cmd, desc in filtered:
            item = ListItem(
                Horizontal(
                    Label(cmd, classes="cmd-name"),
                    Label(desc, classes="cmd-desc"),
                ),
                id=f"cmd-{cmd[1:]}",
            )
            list_view.append(item)

    def action_close(self) -> None:
        self.visible = False
        self.display = False

    def action_execute(self) -> None:
        list_view = self.query_one("#palette-list", ListView)
        if list_view.highlighted_child:
            cmd_id = list_view.highlighted_child.id
            if cmd_id:
                cmd = cmd_id.replace("cmd-", "/")
                self.run_command(cmd)
        self.action_close()

    def run_command(self, cmd: str) -> None:
        if cmd == "/help":
            self.app.notify("Commands: /help, /clear, /model, /skills, /tools, /memory, /settings, /voice, /status, /install, /mcp, /exit")
        elif cmd == "/clear":
            self.app.action_clear_chat()
        elif cmd == "/model":
            self.app.action_command_palette()
        elif cmd == "/skills":
            self.app.switch_screen("skills")
        elif cmd == "/tools":
            self.app.switch_screen("tools")
        elif cmd == "/memory":
            self.app.switch_screen("memory")
        elif cmd == "/settings":
            self.app.switch_screen("settings")
        elif cmd == "/voice":
            self.app.switch_screen("voice")
        elif cmd == "/status":
            self.app.notify("System status: OK")
        elif cmd == "/exit":
            self.app.exit()


from textual.containers import Horizontal