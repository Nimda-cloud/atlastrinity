import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.mcp_server.vibe_server import vibe_prompt

async def test_stream():
    print("Testing Vibe Stream...")
    # This prompt should trigger some reasoning/output
    prompt = "Think about 3 ways to build a seafood app. List them one by one."
    
    # We call vibe_prompt directly (it uses _run_vibe inside)
    # This will log to our standard brain logger which prints to console
    result = await vibe_prompt(
        prompt=prompt,
        cwd=os.getcwd(),
        timeout_s=30
    )
    print("\nFinal Result received.")

if __name__ == "__main__":
    asyncio.run(test_stream())
