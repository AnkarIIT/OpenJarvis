import asyncio

import pytest

from jarvis.config.settings import Settings
from jarvis.mcp.client import MCPClient, MCPTool


@pytest.mark.asyncio
async def test_mcp_call_retries_and_records_latency(monkeypatch):
    settings = Settings()
    settings.mcp.max_retries = 1
    settings.mcp.retry_backoff = 0
    client = MCPClient(settings)
    client.tools = [MCPTool("status", "Status", {}, "memory")]
    class FakeSession:
        async def call_tool(self, name, arguments):
            return {"ok": True}

    client.sessions["memory"] = FakeSession()
    client.server_health["memory"] = {
        "healthy": True,
        "failures": 0,
        "last_error": None,
        "last_latency_ms": None,
        "retries": 0,
    }
    attempts = 0

    async def call_tool(name, arguments):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary failure")
        return {"ok": True}

    monkeypatch.setattr(client.sessions["memory"], "call_tool", call_tool)
    result = await client.call_tool("status", {})

    assert result == {"ok": True}
    assert attempts == 2
    assert client.server_health["memory"]["retries"] == 1
    assert client.server_health["memory"]["last_latency_ms"] is not None
