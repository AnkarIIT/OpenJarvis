"""Fix all MCP servers to use text_result() instead of TextContent dicts."""
import re
from pathlib import Path

files = [
    "jarvis/mcp/servers/filesystem.py",
    "jarvis/mcp/servers/terminal.py",
    "jarvis/mcp/servers/git.py",
    "jarvis/mcp/servers/memory.py",
    "jarvis/mcp/servers/web_search.py",
    "jarvis/mcp/servers/browser.py",
    "jarvis/mcp/servers/desktop.py",
]

PATTERN = re.compile(
    r'return \{"content": \[TextContent\(type="text", text=(.+)\)\]\}'
)

for filepath in files:
    path = Path(filepath)
    content = path.read_text(encoding="utf-8")
    original = content

    # Remove TextContent from mcp.types import
    content = content.replace(
        "from mcp.types import Tool, TextContent, ServerCapabilities",
        "from mcp.types import Tool, ServerCapabilities",
    )

    # Add text_result to the compat import
    content = content.replace(
        "from jarvis.mcp.compat import serialize_tools",
        "from jarvis.mcp.compat import serialize_tools, text_result",
    )

    # Replace TextContent dict returns with text_result() calls
    counter = [0]
    def replacer(match):
        counter[0] += 1
        expr = match.group(1).strip()
        return f"return text_result({expr})"

    content = PATTERN.sub(replacer, content)

    if content != original:
        path.write_text(content, encoding="utf-8")
        print(f"  Fixed: {filepath} ({counter[0]} replacements)")
    else:
        print(f"  No changes: {filepath}")
