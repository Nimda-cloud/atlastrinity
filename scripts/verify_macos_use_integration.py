
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.brain.agents.tetyana import Tetyana
from src.brain.mcp_manager import mcp_manager
from src.brain.logger import logger

async def test_tetyana_macos_use():
    logger.info("🧪 Starting Integration Test: Tetyana + macos-use")
    
    # Initialize Tetyana
    tetyana = Tetyana()
    
    # 1. Define a step that requires macos-use
    # "Open TextEdit"
    step1 = {
        "id": 1,
        "action": "Open TextEdit application",
        "tool": "macos-use", # Hint to use macos-use
        "args": {"identifier": "com.apple.TextEdit"}, # Direct args to skip LLM for this test if possible, or Tetyana logic will handle it
        "expected_result": "TextEdit is running"
    }
    
    logger.info(f"👉 Executing Step 1: {step1['action']}")
    result1 = await tetyana.execute_step(step1, attempt=1)
    logger.info(f"Step 1 Result: {result1}")
    
    if not result1.success:
        logger.error("❌ Step 1 failed")
        return
        
    # extract PID from result if possible (Tetyana might not return it in structured way easily, but let's see)
    
    # 2. Type text
    step2 = {
        "id": 2,
        "action": "Type 'Hello Integration' into TextEdit",
        "tool": "macos-use_type_and_traverse",
        "args": {"text": "Hello Integration Test"},
        "expected_result": "Text typed"
    }
    
    logger.info(f"👉 Executing Step 2: {step2['action']}")
    result2 = await tetyana.execute_step(step2, attempt=1)
    logger.info(f"Step 2 Result: {result2}")
    
    if result2.success:
        logger.info("✅ Integration Test PASSED")
    else:
        logger.error("❌ Step 2 failed")

    await mcp_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(test_tetyana_macos_use())
