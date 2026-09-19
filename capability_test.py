"""Comprehensive capability test for the Jarvis agent loop."""
import asyncio
import sys
import time
import json

from jarvis.agent.loop import AgentLoop
from jarvis.config.settings import load_settings


async def main():
    settings = load_settings()
    settings.llm.max_tokens = 512
    settings.llm.temperature = 0.3
    # Speed up qwen3 by disabling thinking mode
    settings.llm.provider = "ollama"

    print("=== Initializing AgentLoop ===")
    loop = AgentLoop(settings)
    await loop.initialize()

    print(f"Provider: {settings.llm.provider}")
    print(f"Model: {settings.llm.model}")
    print(f"MCP connected: {loop.mcp.is_connected}")
    print(f"MCP tools: {[t.name for t in loop.mcp.tools]}")
    print(f"Skill commands: {len(loop.skill_registry.list_commands())} available")
    print(f"Skill command names: {[c.name for c in loop.skill_registry.list_commands()]}")
    print()

    tests = [
        ("basic_chat", "What is 2+2? Just answer briefly."),
        ("web_search", "Search the web for 'latest ECG early arrhythmia detection research' and tell me what you find."),
        ("system_monitor", "Check the system CPU and memory usage right now."),
        ("code_assistant", "List the functions in the file jarvis/agent/loop.py."),
        ("code_assistant_write", "Create a Python file called test_jarvis_output.py in the current directory with a simple 'hello world' script."),
    ]

    for test_name, prompt in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {test_name}")
        print(f"PROMPT: {prompt}")
        print(f"{'='*60}")
        start = time.time()
        chunks = []
        try:
            async for chunk in loop.run(prompt):
                chunks.append(chunk)
                sys.stdout.write(chunk[:200])
                sys.stdout.flush()
            full_response = "".join(chunks)
            elapsed = time.time() - start
            print(f"\n--- Completed in {elapsed:.1f}s ---")
            print(f"Response length: {len(full_response)} chars")
        except Exception as e:
            elapsed = time.time() - start
            print(f"\n--- FAILED after {elapsed:.1f}s: {e} ---")
            import traceback
            traceback.print_exc()

    # Check audit log
    print(f"\n{'='*60}")
    print("AUDIT LOG CHECK")
    print(f"{'='*60}")
    try:
        from jarvis.agent.audit import AuditLogger
        audit = AuditLogger(settings.mcp.audit_file)
        entries = audit.read_all()
        print(f"Audit entries: {len(entries)}")
        for e in entries[-5:]:
            print(f"  {e.get('tool', '?')} | {e.get('status', '?')} | {e.get('source', '?')}")
    except Exception as e:
        print(f"Audit read error: {e}")

    # Check task persistence
    print(f"\n{'='*60}")
    print("TASK STATE CHECK")
    print(f"{'='*60}")
    try:
        status = await loop.get_status()
        print(f"Last task: {json.dumps(status.get('last_task'), indent=2, default=str)}")
    except Exception as e:
        print(f"Status error: {e}")

    await loop.mcp.disconnect_all()
    print("\n=== Capability test complete ===")


if __name__ == "__main__":
    asyncio.run(main())
