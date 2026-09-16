from __future__ import annotations

from typing import Any
from uuid import uuid4

from jarvis.config.settings import Settings


_CONFIRMATION_SERVERS = {"filesystem", "terminal", "git", "browser", "desktop"}
_READ_ONLY_HINTS = ("list", "read", "get", "status", "diff", "search", "info", "inspect")


def action_policy(settings: Settings, server_name: str, tool_name: str) -> str:
    """Resolve an explicit per-tool policy, with a conservative server fallback."""
    for key in (f"{server_name}:{tool_name}", tool_name, server_name):
        configured = settings.mcp.tool_policies.get(key)
        if configured:
            return configured
    if server_name in _CONFIRMATION_SERVERS:
        normalized = tool_name.lower().replace("-", "_")
        if any(
            normalized.startswith(hint) or f"_{hint}" in normalized
            for hint in _READ_ONLY_HINTS
        ):
            return "allow"
        return "confirm" if settings.mcp.require_confirmation else "allow"
    return "allow"


def requires_confirmation(settings: Settings, server_name: str, tool_name: str = "") -> bool:
    return action_policy(settings, server_name, tool_name) == "confirm"


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
