from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ApprovalScreen(ModalScreen[bool]):
    BINDINGS = [("escape", "deny", "Deny")]

    def __init__(self, tool_name: str, server_name: str, arguments: dict):
        super().__init__()
        self.tool_name = tool_name
        self.server_name = server_name
        self.arguments = arguments

    def compose(self) -> ComposeResult:
        yield Container(
            Vertical(
                Static("JARVIS ACTION APPROVAL", id="approval-title"),
                Static(
                    f"Allow '{self.tool_name}' from '{self.server_name}'?\n"
                    f"Arguments: {self.arguments}",
                    id="approval-details",
                ),
                Horizontal(
                    Button("Approve", id="approve", variant="success"),
                    Button("Deny", id="deny", variant="error"),
                    id="approval-actions",
                ),
                id="approval-container",
            )
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "approve")

    def action_deny(self) -> None:
        self.dismiss(False)
