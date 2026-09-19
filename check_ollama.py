import ollama
import asyncio

c = ollama.AsyncClient(host='http://localhost:11434', timeout=10)

async def main():
    r = await asyncio.wait_for(c.list(), timeout=10)
    # Check if .get works on ListResponse
    print('tags.get("models", []):', hasattr(r, 'get'))
    try:
        val = r.get("models", [])
        print('  Result:', val)
    except Exception as e:
        print(f'  Error: {e}')
    
    # Try accessing via attribute
    print('tags.models:', r.models if hasattr(r, 'models') else 'N/A')
    
    # Check each model
    for m in r.models:
        print(f'  model attr: {m.model}')
        print(f'  has get: {hasattr(m, "get")}')
        try:
            print(f'  m.get("name"): {m.get("name", "MISSING")}')
        except Exception as e:
            print(f'  m.get error: {e}')

asyncio.run(main())
