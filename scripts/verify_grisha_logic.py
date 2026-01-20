import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.agents.grisha import Grisha


async def test_strategy_planning():
    print("Initializing Grisha...")
    grisha = Grisha()

    context = {"cwd": os.path.expanduser("~"), "os": "macOS"}

    task_action = "Remove the application Rectangle.app from /Applications"
    expected_result = "Application is removed and no longer running."

    print(f"\n--- Testing Strategy for Task: {task_action} ---")
    strategy = await grisha._plan_verification_strategy(task_action, expected_result, context)

    print("\n[GENERATED STRATEGY]")
    print(strategy)

    # Check for keywords
    if "ps aux" in strategy or "pgrep" in strategy:
        print("\n[SUCCESS] Strategy includes process check.")
    else:
        print("\n[FAILURE] Strategy missing process check.")

    if "ls" in strategy or "stat" in strategy or "test -e" in strategy:
        print("[SUCCESS] Strategy includes file check.")
    else:
        print("[FAILURE] Strategy missing file check.")


if __name__ == "__main__":
    asyncio.run(test_strategy_planning())
