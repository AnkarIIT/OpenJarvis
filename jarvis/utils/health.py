from __future__ import annotations

import importlib.util
import platform
import sys
from typing import Any

from jarvis.config.settings import Settings
from jarvis.mcp.client import MCPClient
from jarvis.utils.detectors import detect_all_local_ai, get_system_info
from jarvis.agent.llm_client import LLMClient


CORE_IMPORTS = {
    "textual": "textual",
    "pydantic": "pydantic",
    "mcp": "mcp",
    "httpx": "httpx",
    "yaml": "yaml",
}


def build_health_report(settings: Settings) -> dict[str, Any]:
    providers = detect_all_local_ai()
    dependencies = {
        name: importlib.util.find_spec(module) is not None
        for name, module in CORE_IMPORTS.items()
    }
    mcp = MCPClient(settings)
    servers = mcp._resolve_servers()
    llm = LLMClient(settings)
    return {
        "status": "ok" if all(dependencies.values()) else "degraded",
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "supported_python": sys.version_info >= (3, 10),
        },
        "dependencies": dependencies,
        "providers": providers,
        "llm": {
            "configured_provider": settings.llm.provider,
            "configured_model": settings.llm.model,
            "active_provider": llm.provider_name,
            "observability": llm.observability,
        },
        "mcp": {
            "configured": sorted(settings.mcp.servers),
            "eligible_servers": sorted(servers),
            "dangerous_enabled": settings.mcp.allow_dangerous,
            "require_confirmation": settings.mcp.require_confirmation,
            "server_health": mcp.server_health,
        },
        "skills": {
            "enabled": sorted(settings.skills.enabled),
            "paths": [str(path) for path in settings.skills_paths],
        },
    }
