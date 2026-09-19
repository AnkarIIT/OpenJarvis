import mcp.server.runner as r
import inspect

src = inspect.getsource(r)
lines = src.split('\n')
for i, line in enumerate(lines, 1):
    if 'serialize_server_result' in line or 'CallToolResult' in line or '_serialize' in line:
        start = max(0, i-2)
        end = min(len(lines), i+15)
        for j in range(start, end):
            print(f"{j+1}: {lines[j]}")
        print("---")
