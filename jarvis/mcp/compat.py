from __future__ import annotations

from typing import Any, Iterable


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
