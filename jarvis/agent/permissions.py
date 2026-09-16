from __future__ import annotations

from typing import Any
from uuid import uuid4

from jarvis.config.settings import Settings


_CONFIRMATION_SERVERS = {"filesystem", "terminal", "git", "browser", "desktop"}


def requires_confirmation(settings: Settings, server_name: str) -> bool:
    """Return whether an MCP action must be approved before execution."""
    return settings.mcp.require_confirmation and server_name in _CONFIRMATION_SERVERS


def confirmation_required_result(
    tool_name: str,
    server_name: str,
    approval_id: str | None = None,
) -> dict[str, Any]:
    approval_id = approval_id or str(uuid4())
    return {
        "error": "confirmation_required",
        "approval_id": approval_id,
        "message": (
            f"Tool '{tool_name}' from dangerous server '{server_name}' was not executed. "
            f"Explicit user confirmation is required before this action (approval: {approval_id})."
        ),
        "tool": tool_name,
        "server": server_name,
    }
