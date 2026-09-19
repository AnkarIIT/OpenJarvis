"""Quick test: verify memory store works now that sentence-transformers is installed."""
import asyncio
import sys
import time
from jarvis.config.settings import load_settings
from jarvis.memory.vector_store import VectorStore

async def main():
    settings = load_settings()
    settings.memory.enabled = True
    vs = VectorStore(settings)
    await vs.initialize()

    print("=== Testing VectorStore (ChromaDB + sentence-transformers) ===")

    # Add a memory
    start = time.time()
    mem_id = await vs.add_memory("JARVIS is a local AI assistant", {"category": "test"})
    elapsed = time.time() - start
    print(f"Added memory (id={mem_id[:8]}..., took {elapsed:.1f}s)")

    # Search for it
    start = time.time()
    results = await vs.search("JARVIS AI assistant", limit=3)
    elapsed = time.time() - start
    print(f"Search results ({len(results)} found, took {elapsed:.1f}s)")
    for r in results:
        print(f"  - {r['content'][:60]} (score={r['score']:.3f})")

    # List memories
    mems = await vs.list_memories()
    print(f"Total memories: {len(mems)}")

    # Test secret rejection
    try:
        await vs.add_memory("api_key=sk-1234567890abcdef", {})
        print("ERROR: secret was NOT rejected!")
    except ValueError as e:
        print(f"Secret correctly rejected: {e}")

    print("\n=== VectorStore test complete ===")

asyncio.run(main())
