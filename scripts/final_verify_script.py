import asyncio
import logging
import os
from pathlib import Path

from mcp_server import vibe_server
from mcp_server.vibe_server import Context

logging.basicConfig(level=logging.INFO)

# Load .env
env_path = Path(".env")
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                os.environ[k] = v
    print("Loaded .env")

async def test_final_verification():
    print("--- Starting Final Verification ---")

    ctx = Context(request_id="test-final", client_id="test-client")

    # We want to force a Copilot action.
    # Since we fixed the templates, we can just use gpt-4o with auto-approve agent.

    print("Executing Vibe prompt to create a test file...")
    result = await vibe_server.vibe_prompt(
        ctx=ctx,
        prompt="Створи файл scripts/final_verify.py з текстом 'Verification Success'",
        model="gpt-4o",
        agent="auto-approve",
    )

    print(f"Result: {result}")

    # Check if file exists
    if os.path.exists("scripts/final_verify.py"):
        print("✅ SUCCESS: scripts/final_verify.py was created!")
        with open("scripts/final_verify.py") as f:
            print(f"File content: {f.read()}")
    else:
        print("❌ FAILURE: scripts/final_verify.py was NOT created.")

if __name__ == "__main__":
    asyncio.run(test_final_verification())
