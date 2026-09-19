"""Test MCP memory tools and a simple agent loop run."""
import asyncio
import json
import sys
import time
from jarvis.mcp.client import MCPClient
from jarvis.config.settings import load_settings
from jarvis.agent.loop import AgentLoop


async def test_mcp_memory():
    """Test the memory MCP server with correct tool names."""
    settings = load_settings()
    mcp = MCPClient(settings)
    await mcp.connect_all()
    print(f"MCP tools: {[(t.name, t.server_name) for t in mcp.tools]}")

    # Store a memory
    r = await mcp.call_tool("add_memory", {"content": "Jarvis was tested"})
    print(f"add_memory: {str(r)[:200]}")

    # List memories
    r = await mcp.call_tool("list_memories", {})
    print(f"list_memories: {str(r)[:300]}")

    # Read memory
    r = await mcp.call_tool("search_memory", {"query": "jarvis"})
    print(f"search_memory: {str(r)[:300]}")

    # Delete memory (find id from search results)
    import re
    ids = re.findall(r"\[([^\]]+)\]", str(r))
    if ids:
        r = await mcp.call_tool("delete_memory", {"id": ids[0]})
        print(f"delete_memory: {str(r)[:200]}")
    else:
        print("delete_memory: skipped (no id found)")

    await mcp.disconnect_all()
    print("=== MCP memory test done ===\n")


async def test_simple_agent():
    """Test the full agent loop with a simple prompt that uses a skill."""
    settings = load_settings()
    settings.llm.max_tokens = 512
    settings.llm.temperature = 0.1

    loop = AgentLoop(settings)
    await loop.initialize()
    print(f"Provider: {settings.llm.provider}, Model: {settings.llm.model}")
    print(f"MCP tools: {[(t.name, t.server_name) for t in loop.mcp.tools]}")
    print(f"Skill commands: {len(loop.skill_registry.list_commands())}")

    # Simple prompt that should trigger a skill (system_monitor)
    prompt = "Check the CPU usage on this machine."
    print(f"\n>>> Prompt: {prompt}")
    start = time.time()
    chunks = []
    try:
        async for chunk in loop.run(prompt):
            chunks.append(chunk)
            sys.stdout.write(chunk[:200])
            sys.stdout.flush()
        full = "".join(chunks)
        elapsed = time.time() - start
        print(f"\n--- Completed in {elapsed:.1f}s, {len(full)} chars ---")
    except Exception as e:
        elapsed = time.time() - start
        print(f"\n--- FAILED after {elapsed:.1f}s: {e} ---")
        import traceback
        traceback.print_exc()

    # Check observability
    print(f"\nLLM Observability: {json.dumps(loop.llm.observability, indent=2)}")

    await loop.mcp.disconnect_all()


async def main():
    await test_mcp_memory()
    await test_simple_agent()


if __name__ == "__main__":
    asyncio.run(main())
