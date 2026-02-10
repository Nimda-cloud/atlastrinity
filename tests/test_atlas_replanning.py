import asyncio
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(current_dir, "..")
sys.path.insert(0, os.path.abspath(root))

from unittest.mock import AsyncMock, MagicMock

from src.brain.agents.atlas import Atlas


async def test_replanning_feedback():
    print("Testing Atlas replanning feedback...")

    # Mock dependencies
    atlas = Atlas()
    atlas.llm = AsyncMock()
    atlas.llm_deep = AsyncMock()
    atlas.use_sequential_thinking = AsyncMock()

    # Mock successful reasoning
    atlas.use_sequential_thinking.return_value = {
        "success": True,
        "analysis": "Test simulation analysis",
    }

    # Mock LLM response for planning
    mock_response = MagicMock()
    mock_response.content = '{"goal": "Test Goal", "steps": [{"id": 1, "realm": "macos-use", "action": "test", "voice_action": "тест", "expected_result": "done"}]}'
    atlas.llm.ainvoke.return_value = mock_response

    # Scenario: Replanning with feedback
    enriched_request = {
        "enriched_request": "Scan network",
        "simulation_result": "Error: Missing IP addresses for Kali and MikroTik.",
    }

    await atlas.create_plan(enriched_request)

    # Check if use_sequential_thinking was called with the feedback
    args, kwargs = atlas.use_sequential_thinking.call_args
    simulation_prompt = args[0]

    # Verify feedback presence in the prompt
    print("\nVerifying simulation prompt...")
    if "PREVIOUS FAILURE FEEDBACK" in simulation_prompt:
        print("✅ SUCCESS: Previous failure feedback found in simulation prompt.")
    else:
        print("❌ FAILURE: Previous failure feedback NOT found in simulation prompt.")

    if "Missing IP addresses for Kali and MikroTik" in simulation_prompt:
        print("✅ SUCCESS: Specific feedback content found.")
    else:
        print("❌ FAILURE: Specific feedback content NOT found.")

    # Verify logic
    print("\nSimulation Prompt used:\n", simulation_prompt)


if __name__ == "__main__":
    asyncio.run(test_replanning_feedback())
