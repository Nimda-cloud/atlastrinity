"""Final test of raptor-mini alias with vibe"""

import os
import subprocess
import time

os.chdir("/Users/hawk/Documents/GitHub/atlastrinity")

# Start proxy
print("🚀 Starting Copilot proxy...")
proxy_proc = subprocess.Popen(
    ["python3", "scripts/copilot_proxy.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
time.sleep(3)

# Test using alias "raptor-mini"
print("\n🧪 Testing 'raptor-mini' alias (should map to gpt-5-mini)...")
result = subprocess.run(
    [
        "vibe",
        "--model",
        "raptor-mini",
        "-p",
        "What is 7 * 8? Answer only with the number.",
        "--output",
        "text",
    ],
    capture_output=True,
    text=True,
    timeout=60,
)

proxy_proc.terminate()

if result.returncode == 0:
    print("✅ SUCCESS: raptor-mini alias works!")
    print(f"Response: {result.stdout.strip()}")
else:
    print(f"❌ FAILED: {result.returncode}")
    print(f"Error: {result.stderr}")

print("\n✓ Test complete")
