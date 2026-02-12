import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.mcp_server.vibe_server import vibe_prompt


async def demo_visibility():

    cwd = os.getcwd()

    # Simple prompt that requires Vibe to think and write a file
    prompt = "Think about why seafood e-commerce is profitable for 3 seconds, then create a file called 'vibe_check.txt' with the text 'Vibe is working in the correct folder!' and return the result."

    # This will trigger the logger inside vibe_server.py
    # and you will see [VIBE-LIVE] in the output below.
    await vibe_prompt(prompt=prompt, cwd=cwd, timeout_s=60)

    test_file = Path(cwd) / "vibe_check.txt"
    if test_file.exists():
        test_file.read_text()
        # Cleanup
        os.remove(test_file)
    else:
        pass


if __name__ == "__main__":
    asyncio.run(demo_visibility())
