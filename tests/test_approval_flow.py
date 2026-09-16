import pytest

from jarvis.agent.loop import AgentLoop
from jarvis.config.settings import Settings
from jarvis.mcp.client import MCPTool


@pytest.mark.asyncio
async def test_dangerous_tool_uses_approval_handler(monkeypatch):
    loop = AgentLoop(Settings())
    tool = MCPTool("run_command", "Run a command", {}, "terminal")
    loop.mcp.tools = [tool]
    called = []

    async def approve(tool_name, server_name, arguments):
        called.append((tool_name, server_name, arguments))
        return True

    loop.approval_handler = approve

    async def call_tool(tool_name, arguments):
        return {"ok": True}

    monkeypatch.setattr(loop.mcp, "call_tool", call_tool)
    result = await loop._execute_tool("run_command", {"command": "echo hi"})

    assert result == {"ok": True}
    assert called == [("run_command", "terminal", {"command": "echo hi"})]


@pytest.mark.asyncio
async def test_dangerous_tool_is_denied_when_approval_is_rejected():
    loop = AgentLoop(Settings())
    loop.mcp.tools = [MCPTool("run_command", "Run a command", {}, "terminal")]

    async def deny(tool_name, server_name, arguments):
        return False

    loop.approval_handler = deny
    result = await loop._execute_tool("run_command", {"command": "del important.txt"})

    assert result["error"] == "confirmation_required"
    assert result["tool"] == "run_command"
