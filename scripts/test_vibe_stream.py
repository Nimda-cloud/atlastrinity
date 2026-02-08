import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.mcp_server.vibe_server import vibe_prompt


async def test_stream():
    print("Testing Vibe Stream...")
    # This prompt should trigger some reasoning/output
    prompt = "Think about 3 ways to build a seafood app. List them one by one."

    # We call vibe_prompt directly (it uses _run_vibe inside)
    # This will log to our standard brain logger which prints to console
    # Mock context
    class MockContext:
        async def info(self, msg):
            print(f"[CTX] INFO: {msg}")

        async def error(self, msg):
            print(f"[CTX] ERROR: {msg}")

    ctx = MockContext()

    await vibe_prompt(ctx=ctx, prompt=prompt, cwd=os.getcwd(), timeout_s=30)
    print("\nFinal Result received.")


if __name__ == "__main__":
    asyncio.run(test_stream())
