from jarvis.config.settings import Settings
from jarvis.mcp.client import MCPClient


def test_mcp_health_starts_empty_and_resolves_safe_servers():
    client = MCPClient(Settings())
    assert client.server_health == {}
    servers = client._resolve_servers()
    assert "memory" in servers
    assert "terminal" not in servers
