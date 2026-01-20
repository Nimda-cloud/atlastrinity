import asyncio
import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from src.mcp_server.vibe_server import vibe_prompt


async def demo_visibility():
    print("=== VIBE VISIBILITY DEMO ===")
    print("This script will demonstrate:")
    print("1. [VIBE-LIVE] logs going to terminal/Electron.")
    print("2. Vibe working in the same folder.")
    print("3. File creation in the current repository.\n")

    cwd = os.getcwd()
    print(f"Current System CWD: {cwd}")

    # Simple prompt that requires Vibe to think and write a file
    prompt = "Think about why seafood e-commerce is profitable for 3 seconds, then create a file called 'vibe_check.txt' with the text 'Vibe is working in the correct folder!' and return the result."

    # This will trigger the logger inside vibe_server.py
    # and you will see [VIBE-LIVE] in the output below.
    await vibe_prompt(prompt=prompt, cwd=cwd, timeout_s=60)

    print("\n=== VERIFICATION ===")
    test_file = Path(cwd) / "vibe_check.txt"
    if test_file.exists():
        content = test_file.read_text()
        print(f"✅ Success! File created at: {test_file}")
        print(f"📄 Content: {content}")
        # Cleanup
        os.remove(test_file)
    else:
        print("❌ Error: File was not created.")


if __name__ == "__main__":
    asyncio.run(demo_visibility())
