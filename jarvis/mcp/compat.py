from __future__ import annotations

from typing import Any, Iterable

from mcp.types import CallToolResult, TextContent


def serialize_tools(tools: Iterable[Any]) -> list[dict[str, Any]]:
    """Return MCP tool dictionaries compatible across mcp package versions."""
    result = []
    for tool in tools:
        if hasattr(tool, "model_dump"):
            result.append(tool.model_dump(by_alias=True, exclude_none=True))
        elif isinstance(tool, dict):
            result.append(tool)
        else:
            result.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": getattr(tool, "inputSchema", getattr(tool, "input_schema", {})),
            })
    return result


def text_result(text: str) -> CallToolResult:
    """Create a CallToolResult with a single TextContent block.

    In mcp >= 2.x the server runner validates handler return values against the
    CallToolResult model.  Returning a raw dict with TextContent *instances*
    (as the codebase did for mcp 1.x) triggers a Pydantic ValidationError
    because the validator cannot coerce a TextContent object when it appears
    inside a dict being validated.  Returning a proper CallToolResult ensures
    ``model_dump()`` is called, which serialises TextContent to a dict.
    """
    return CallToolResult(content=[TextContent(type="text", text=text)])
