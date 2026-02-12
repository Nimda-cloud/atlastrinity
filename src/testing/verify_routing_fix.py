import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


async def test_routing():

    from src.brain.agents.tetyana import Tetyana

    # Mock dependencies
    tetyana = Tetyana()
    repo_root = str(Path.cwd().absolute())
    args = {"prompt": "hi", "cwd": repo_root}

    # We need to mock the internal _call_mcp_direct or just call it
    # Since we want to test the logic inside _call_mcp_direct, let's call it
    # Note: we need to handle the fact that it's a private method

    try:
        # We want to test re-routing in _call_mcp_direct

        await tetyana._call_mcp_direct("vibe", "vibe_prompt", args)

        expected_workspace = str(Path.home() / "AtlasProjects")
        actual_cwd = args["cwd"]

        if actual_cwd == expected_workspace:
            pass
        else:
            pass

    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(test_routing())
