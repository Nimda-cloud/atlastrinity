#!/usr/bin/env python3
"""Quick test for raptor-mini alias"""

import os
import subprocess
import time
from pathlib import Path

PROJECT_ROOT = Path("/Users/hawk/Documents/GitHub/atlastrinity")
os.chdir(PROJECT_ROOT)

# Start proxy first
print("Starting Copilot proxy...")
proxy_proc = subprocess.Popen(
    ["python3", "scripts/copilot_proxy.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)
time.sleep(2)

# Test raptor-mini
print("\n🧪 Testing raptor-mini (should now work)...")
result = subprocess.run(
    ["vibe", "-p", "Say 'raptor works' if you're raptor-mini", "--output", "text"],
    capture_output=True,
    text=True,
    timeout=30,
)

if result.returncode == 0:
    print("✅ SUCCESS: raptor-mini is working!")
    print(f"Response: {result.stdout.strip()[:200]}")
else:
    print(f"❌ FAILED: {result.returncode}")
    print(f"Error: {result.stderr[:500]}")

proxy_proc.terminate()
print("\n✓ Proxy terminated")
