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


async def test_final_verification():

    ctx = Context(request_id="test-final", client_id="test-client")

    # We want to force a Copilot action.
    # Since we fixed the templates, we can just use gpt-4o with auto-approve agent.

    await vibe_server.vibe_prompt(
        ctx=ctx,
        prompt="Створи файл scripts/final_verify.py з текстом 'Verification Success'",
        model="gpt-4o",
        agent="auto-approve",
    )

    # Check if file exists
    if os.path.exists("scripts/final_verify.py"):
        with open("scripts/final_verify.py"):
            pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(test_final_verification())
