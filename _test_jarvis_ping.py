"""Test jarvis/ping endpoint directly — print server traceback."""
import subprocess, sys, time, json, urllib.request, urllib.error

proc = subprocess.Popen(
    [sys.executable, "martian_device.py", "api", "--port", "5003"],
    cwd=r"C:\Codes\jarvis-agent",
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    text=True, bufsize=1,
)
time.sleep(4)

try:
    req = urllib.request.Request(
        "http://localhost:5003/jarvis/ping",
        data=json.dumps({"message": "test"}).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        print("SUCCESS:", r.read().decode()[:300])
except urllib.error.HTTPError as e:
    print("HTTP ERROR", e.code)
    print("BODY:", e.read().decode()[:500])
except Exception as e:
    print("ERROR:", type(e).__name__, str(e))

print("\n--- SERVER OUTPUT (last 2000 chars) ---")
out = proc.stdout.read()
print(out[-2000:] if out else "(no output)")

proc.terminate()
proc.wait(timeout=5)
