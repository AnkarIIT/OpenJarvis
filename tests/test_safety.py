from jarvis.config.settings import Settings
from jarvis.mcp.client import MCPClient


def test_dangerous_mcp_servers_are_disabled_by_default():
    settings = Settings()
    servers = MCPClient(settings)._resolve_servers()
    assert "memory" in servers
    assert "web_search" in servers
    assert "terminal" not in servers
    assert "filesystem" not in servers
    assert "browser" not in servers


def test_dangerous_mcp_servers_can_be_explicitly_enabled():
    settings = Settings()
    settings.mcp.allow_dangerous = True
    servers = MCPClient(settings)._resolve_servers()
    assert "terminal" in servers
    assert "filesystem" in servers
    assert "browser" in servers


def test_mcp_enabled_server_filter_is_applied():
    settings = Settings()
    settings.mcp.enabled_servers = ["web_search"]
    servers = MCPClient(settings)._resolve_servers()
    assert set(servers) == {"web_search"}
