import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.brain.core.orchestration.orchestrator import Trinity as Orchestrator
from src.brain.mcp.mcp_manager import mcp_manager


async def run_autonomous_google_reg():

    orchestrator = Orchestrator()
    await orchestrator.initialize()

    # Detailed instruction for the agents
    data_prompt = (
        "Open Google Chrome, navigate to the Google Account Creation page, and start registering a new account with these details:\n"
        "- First Name: Master\n"
        "- Last Name: Atlas\n"
        "- Desired Username: master.atlas.2026\n"
        "- Password: TrinityPassword2026!\n"
        "- Birthday: October 10, 1990\n"
        "- Gender: Rather not say\n"
        "Proceed through the steps (Name -> Birthday -> Username -> Password). "
        "Stop only if it asks for a phone number for SMS verification."
    )

    try:
        # Run the full pipeline
        # Using a timeout to prevent infinite loops in demo
        await asyncio.wait_for(orchestrator.run(data_prompt), timeout=600)

    except TimeoutError:
        pass
    except Exception:
        pass
    finally:
        await mcp_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(run_autonomous_google_reg())
