import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.brain.core.orchestration.orchestrator import Trinity as Orchestrator
from src.brain.logger import logger
from src.brain.mcp_manager import mcp_manager


async def run_test():
    logger.info("🚀 LAST ATTEMPT: Final verification of Native macOS Tools...")

    # Використовуємо максимально чіткий промпт для Атласа
    task = """
    ACTION: Execute the following sequence of commands immediately:
    STEP 1: Open 'Calculator' application.
    STEP 2: Use window management to move Calculator window to (200, 200).
    STEP 3: Use window management to resize Calculator window to (200, 400). Note ACTUAL result.
    STEP 4: Type digits '7', '7', '7' into the Calculator.
    STEP 5: Take an OCR analysis of the screen and confirm if you see '777'.
    """

    orchestrator = Orchestrator()
    await orchestrator.initialize()

    try:
        await orchestrator.run(task)
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        await mcp_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(run_test())
