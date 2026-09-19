"""Quick capability tests for Jarvis skills - no LLM needed."""
import asyncio
import json
import sys
from jarvis.skills.registry import SkillRegistry
from jarvis.config.settings import load_settings


async def main():
    settings = load_settings()
    registry = SkillRegistry(settings)
    await registry.initialize()

    print(f"=== {len(registry.list_commands())} skill commands loaded ===\n")

    # Test system_monitor
    print("=== system_monitor.cpu_info ===")
    r = await registry.execute_command("cpu_info")
    print(json.dumps(r, indent=2, default=str)[:500])
    print()

    print("=== system_monitor.disk_info ===")
    r = await registry.execute_command("disk_info")
    print(json.dumps(r, indent=2, default=str)[:500])
    print()

    # Test code_assistant with correct param names
    print("=== code_assistant.list_functions (file=) ===")
    r = await registry.execute_command("list_functions", file="jarvis/agent/loop.py")
    print(str(r)[:800])
    print()

    print("=== code_assistant.find_todos (path=) ===")
    r = await registry.execute_command("find_todos", path="jarvis/agent")
    print(str(r)[:500])
    print()

    # Test memory MCP server
    print("=== MCP memory server ===")
    from jarvis.mcp.client import MCPClient
    mcp = MCPClient(settings)
    await mcp.connect_all()
    print(f"MCP tools: {[(t.name, t.server_name) for t in mcp.tools]}")

    # Test memory MCP: store and retrieve
    r = await mcp.call_tool("add_memory", {"content": "hello from jarvis test"})
    print(f"Store result: {str(r)[:200]}")
    r = await mcp.call_tool("list_memories", {})
    print(f"List result: {str(r)[:300]}")
    r = await mcp.call_tool("search_memory", {"query": "jarvis"})
    print(f"Read result: {str(r)[:200]}")
    import re
    ids = re.findall(r"\[([^\]]+)\]", str(r))
    if ids:
        r = await mcp.call_tool("delete_memory", {"id": ids[0]})
        print(f"Delete result: {str(r)[:200]}")
    else:
        print("Delete: skipped (no id found)")

    await mcp.disconnect_all()
    print("\n=== All capability tests done ===")


if __name__ == "__main__":
    asyncio.run(main())
