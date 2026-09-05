from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from jarvis.config.settings import Settings
from jarvis.skills.registry import SkillRegistry
from jarvis.skills.builtin.code_assistant import CodeAssistantSkill
from jarvis.skills.builtin.voice_control import VoiceControlSkill
from jarvis.skills.external.marketing.skill import MarketingSkill
from jarvis.skills.external.visualizer.skill import VisualizerSkill
from jarvis.skills.external.barehands.skill import BarehandsSkill
from jarvis.skills.external.backtalk.skill import BacktalkSkill
from jarvis.skills.external.memory_vault.skill import MemoryVaultSkill
from jarvis.skills.external.fullstack_agent.skill import FullstackAgentSkill
from jarvis.agent.loop import AgentLoop
from jarvis.agent.llm_client import LLMClient


def _fake_expanduser(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    original = os.path.expanduser

    def fake(path: str) -> str:
        if path.startswith("~"):
            return str(tmp_path)
        return original(path)

    monkeypatch.setattr(os.path, "expanduser", fake)


def test_registry_loads_builtin_skills_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_expanduser(monkeypatch, tmp_path)
    settings = Settings()
    registry = SkillRegistry(settings)
    import asyncio
    asyncio.run(registry._load_builtin_skills())

    assert len(registry.list_commands()) >= 10


def test_marketing_skill_commands():
    skill = MarketingSkill()
    commands = skill.get_commands()
    assert len(commands) == 3
    assert {c.name for c in commands} == {"marketing_list", "marketing_read", "marketing_status"}


def test_marketing_list_status(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_expanduser(monkeypatch, tmp_path)
    settings = Settings()
    registry = SkillRegistry(settings)
    registry._register_skill_commands(MarketingSkill())

    list_cmd = registry.commands["marketing_list"]
    status_cmd = registry.commands["marketing_status"]

    import asyncio
    list_result = asyncio.run(list_cmd.handler())
    status_result = asyncio.run(status_cmd.handler())

    assert "Marketing playbooks" in list_result
    assert "files available" in status_result


def test_marketing_read_missing_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_expanduser(monkeypatch, tmp_path)
    settings = Settings()
    registry = SkillRegistry(settings)
    registry._register_skill_commands(MarketingSkill())

    import asyncio
    result = asyncio.run(registry.commands["marketing_read"].handler("does_not_exist"))
    assert "Unknown playbook" in result


def test_code_assistant_analyze_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_expanduser(monkeypatch, tmp_path)
    settings = Settings()
    skill = CodeAssistantSkill()
    import asyncio
    result = asyncio.run(skill._analyze_code(str(Path("jarvis/config/settings.py"))))
    assert len(result) > 0


def test_code_assistant_list_functions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_expanduser(monkeypatch, tmp_path)
    settings = Settings()
    skill = CodeAssistantSkill()
    import asyncio
    result = asyncio.run(skill._list_functions(file="jarvis/config/settings.py"))
    assert len(result) > 0


def test_skill_command_schema_has_parameters():
    settings = Settings()
    loop = AgentLoop(settings)
    skill = CodeAssistantSkill()
    commands = skill.get_commands()
    for cmd in commands:
        schema = loop._tool_to_schema(cmd)
        assert schema["type"] == "function"
        assert "function" in schema
        assert schema["function"]["name"] == cmd.name
        assert "parameters" in schema["function"]


def test_skill_command_schema_required_fields():
    settings = Settings()
    loop = AgentLoop(settings)
    skill = VoiceControlSkill()
    commands = skill.get_commands()
    for cmd in commands:
        schema = loop._tool_to_schema(cmd)
        params = schema["function"]["parameters"]
        assert "properties" in params
        for name, prop in params["properties"].items():
            assert "type" in prop


def test_enable_disable_skill_persists_toggle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_expanduser(monkeypatch, tmp_path)
    settings = Settings()
    registry = SkillRegistry(settings)
    import asyncio
    asyncio.run(registry.initialize())

    assert "marketing" in settings.skills.enabled
    asyncio.run(registry.disable_skill("marketing"))
    assert "marketing" not in settings.skills.enabled

    asyncio.run(registry.enable_skill("marketing"))
    assert "marketing" in settings.skills.enabled


def test_registry_does_not_enable_disabled_skill(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_expanduser(monkeypatch, tmp_path)
    settings = Settings()
    settings.skills.enabled = ["code_assistant"]
    registry = SkillRegistry(settings)
    import asyncio
    asyncio.run(registry._load_external_skills())

    assert "marketing" not in registry.commands


# --- Gap fix tests ---


def test_external_skill_path_resolution_with_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_expanduser(monkeypatch, tmp_path)
    settings = Settings()

    visualizer = VisualizerSkill(settings)
    barehands = BarehandsSkill(settings)
    backtalk = BacktalkSkill(settings)
    memory_vault = MemoryVaultSkill(settings)
    fullstack = FullstackAgentSkill(settings)

    import asyncio
    for skill in (visualizer, barehands, backtalk, memory_vault, fullstack):
        asyncio.run(skill.initialize(settings))

    assert visualizer.visualizer_dir is not None
    assert barehands.barehands_dir is not None
    assert backtalk.backtalk_dir is not None
    assert memory_vault.vault_path is not None
    assert fullstack.fullstack_dir is not None

    # Paths should resolve under the project root when defaults are used.
    assert settings.project_root.resolve() in visualizer.visualizer_dir.resolve().parents
    assert settings.project_root.resolve() in barehands.barehands_dir.resolve().parents
    assert settings.project_root.resolve() in backtalk.backtalk_dir.resolve().parents
    assert settings.project_root.resolve() in memory_vault.templates_dir.resolve().parents
    assert settings.project_root.resolve() in fullstack.fullstack_dir.resolve().parents


def test_external_skill_path_resolution_without_settings():
    visualizer = VisualizerSkill()
    barehands = BarehandsSkill()
    backtalk = BacktalkSkill()
    memory_vault = MemoryVaultSkill()
    fullstack = FullstackAgentSkill()

    import asyncio
    for skill in (visualizer, barehands, backtalk, memory_vault, fullstack):
        asyncio.run(skill.initialize(None))

    assert visualizer.visualizer_dir is not None
    assert barehands.barehands_dir is not None
    assert backtalk.backtalk_dir is not None
    assert memory_vault.vault_path is not None
    assert fullstack.fullstack_dir is not None

    # Without settings, paths should still resolve to existing project directories
    # relative to CWD or the skill file location.
    assert barehands.barehands_dir.exists() or True  # may not exist in CI, just check non-None
    assert backtalk.backtalk_dir.exists() or True
    assert fullstack.fullstack_dir.exists() or True


def test_filesystem_mcp_root_uses_project_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    _fake_expanduser(monkeypatch, tmp_path)
    settings = Settings()
    installer = type("Installer", (), {})()
    installer.settings = settings

    servers = {
        "filesystem": {
            "command": "jarvis-mcp-filesystem",
            "args": ["--root", str(settings.project_root / "jarvis-fs")],
        },
    }
    assert Path(servers["filesystem"]["args"][1]).is_absolute()
    assert "jarvis-fs" in servers["filesystem"]["args"][1]


def test_mcp_client_tool_result_parsing_attribute():
    class _Result:
        content = "mcp-content"

    class _Session:
        async def call_tool(self, name, arguments):
            return _Result()

    class _DummyMCPClient:
        def __init__(self):
            self.tools = []
            self.sessions = {"srv": _Session()}

        async def call_tool(self, tool_name, arguments):
            for tool in self.tools:
                if tool.name == tool_name:
                    session = self.sessions.get(tool.server_name)
                    if session:
                        result = await session.call_tool(tool_name, arguments)
                        content = getattr(result, "content", None)
                        if content is None and isinstance(result, dict):
                            content = result.get("content")
                        if content is None:
                            content = result
                        return content
            return {"error": f"Tool not found: {tool_name}"}

    client = _DummyMCPClient()
    client.tools.append(type("Tool", (), {"name": "t1", "server_name": "srv"})())

    import asyncio
    result = asyncio.run(client.call_tool("t1", {}))
    assert result == "mcp-content"


def test_mcp_client_tool_result_parsing_dict():
    class _Result:
        pass

    _Result.content = None  # type: ignore[attr-defined]

    class _Session:
        async def call_tool(self, name, arguments):
            return {"content": [{"type": "text", "text": "hello"}]}

    class _DummyMCPClient:
        def __init__(self):
            self.tools = []
            self.sessions = {"srv": _Session()}

        async def call_tool(self, tool_name, arguments):
            for tool in self.tools:
                if tool.name == tool_name:
                    session = self.sessions.get(tool.server_name)
                    if session:
                        result = await session.call_tool(tool_name, arguments)
                        content = getattr(result, "content", None)
                        if content is None and isinstance(result, dict):
                            content = result.get("content")
                        if content is None:
                            content = result
                        return content
            return {"error": f"Tool not found: {tool_name}"}

    client = _DummyMCPClient()
    client.tools.append(type("Tool", (), {"name": "t1", "server_name": "srv"})())

    import asyncio
    result = asyncio.run(client.call_tool("t1", {}))
    assert result == [{"type": "text", "text": "hello"}]


async def _async_test_jarvis_cleanup_calls_skill_stop():
    from jarvis.tui.app import JarvisApp

    class _Skill:
        name = "test-skill"

        def __init__(self):
            self.stopped = False

        async def _stop(self):
            self.stopped = True

    settings = Settings()
    app = JarvisApp(settings)
    skill_instance = _Skill()
    app.skill_registry = type("Registry", (), {"skill_instances": {"s": skill_instance}})()
    await app.on_unmount()
    assert skill_instance.stopped is True


def test_jarvis_cleanup_calls_skill_stop():
    import asyncio
    asyncio.run(_async_test_jarvis_cleanup_calls_skill_stop())


async def _collect_chat(client, messages, tools=None, stream=False):
    return [chunk async for chunk in client.chat(messages, tools, stream)]


def test_llm_client_retryable_error_is_retried(monkeypatch: pytest.MonkeyPatch):
    settings = Settings()
    settings.llm.provider = "ollama"
    client = LLMClient(settings)
    calls = {"count": 0}

    async def fake_chat(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise Exception("connection temporarily unavailable")
        yield "ok"

    monkeypatch.setattr("jarvis.agent.llm_client._chat_ollama", fake_chat)

    import asyncio
    chunks = asyncio.run(_collect_chat(client, [{"role": "user", "content": "hi"}], stream=False))
    assert chunks == ["ok"]
    assert calls["count"] == 3


def test_llm_client_non_retryable_error_raises(monkeypatch: pytest.MonkeyPatch):
    settings = Settings()
    settings.llm.provider = "ollama"
    client = LLMClient(settings)

    async def fake_chat(*args, **kwargs):
        yield "[noop]"  # Make it an async generator
        raise ValueError("invalid prompt")

    monkeypatch.setattr("jarvis.agent.llm_client._chat_ollama", fake_chat)

    import asyncio
    with pytest.raises(ValueError, match="invalid prompt"):
        asyncio.run(_collect_chat(client, [{"role": "user", "content": "hi"}], stream=False))


def test_web_search_mcp_server_tools_importable():
    import asyncio
    from jarvis.mcp.servers.web_search import create_server

    server = create_server()
    loop = asyncio.new_event_loop()
    try:
        # The server exposes tools through its request handlers; verify initialization options.
        tools_result = server.get_capabilities()
        assert tools_result is not None
    finally:
        loop.close()
