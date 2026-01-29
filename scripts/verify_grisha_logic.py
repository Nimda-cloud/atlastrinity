import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.agents.grisha import Grisha


async def test_strategy_planning():
    print("\n[INFO] This test script is deprecated.")
    print("[INFO] The method _plan_verification_strategy no longer exists in Grisha.")
    print("[INFO] Grisha now uses a 3-phase verification architecture:")
    print("  Phase 1: _analyze_verification_goal (strategy planning)")
    print("  Phase 2: Tool execution via MCP")
    print("  Phase 3: _form_logical_verdict (verdict formation)")
    print("\n[INFO] To test Grisha, use the full verify_step() method instead.")

    # Original test code commented out - method no longer exists
    # context = {"cwd": os.path.expanduser("~"), "os": "macOS"}
    # task_action = "Remove the application Rectangle.app from /Applications"
    # expected_result = "Application is removed and no longer running."
    # strategy = await grisha._plan_verification_strategy(task_action, expected_result, context)


if __name__ == "__main__":
    asyncio.run(test_strategy_planning())
