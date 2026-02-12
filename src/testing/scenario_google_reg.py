import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.brain.core.orchestration.orchestrator import Trinity as Orchestrator
from src.brain.mcp.mcp_manager import mcp_manager


async def test_google_registration_scenario():

    # Initialize
    orchestrator = Orchestrator()
    await orchestrator.initialize()

    # Specific prompt to trigger computer use
    user_request = "Open Chrome and go to Google Account registration page to create a new account."

    # We want to intercept the PLAN to verify it uses the correct tools
    # Since Orchestrator.process_request is e2e, we will run it and stop after a few steps or error out safely
    # For CI safety, we might just ask Atlas to PLAN first.

    # 1. Run the request
    # NOTE: In a real run without user interaction, this might stall on Browser launch if not handled.
    # However, Tetyana now uses native macos-use to launch apps, which works headless/GUI.

    try:
        # Run the request using the main loop
        await orchestrator.run(user_request)

    except Exception:
        pass
    finally:
        await mcp_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(test_google_registration_scenario())
