import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.messages import HumanMessage

from src.brain.agents.tetyana import StepResult
from src.brain.core.orchestration.orchestrator import SystemState, Trinity


async def test_confirmation_flow():

    # 1. Setup Mock Trinity
    trinity = Trinity()
    trinity.state = {
        "messages": [HumanMessage(content="Make me a coffee")],
        "system_state": SystemState.IDLE.value,
        "current_plan": MagicMock(steps=[{"id": "1", "action": "Ask oleg for coffee"}]),
        "step_results": [],
        "error": None,
        "logs": [],
    }

    # Mock Tetyana and Atlas to control output
    trinity.tetyana.execute_step = AsyncMock()
    trinity.atlas.decide_for_user = AsyncMock(return_value="Yes, take espresso.")
    trinity._speak = AsyncMock()
    trinity._log = AsyncMock()

    # Simulate Tetyana requesting consent
    trinity.tetyana.execute_step.side_effect = [
        StepResult(
            step_id="1",
            success=False,
            result="Need coffee type",
            error="need_user_input",
            voice_message="What coffee?",
        ),
        StepResult(
            step_id="1",
            success=True,
            result="Brewing espresso",
            thought="User (Atlas) said espresso",
        ),
    ]

    # 2. Run execute_node with timeout simulation
    # We modify the timeout in config temporarily if needed, but here we can just wait

    # For testing, we might need to mock the timeout in orchestrator or just let it run if it's short
    # Since I can't easily change the code's sleep during test without more mocks,
    # I'll just check if the logic holds.

    # Trigger execution via the recursive orchestrator which handles retries
    steps = [{"id": "1", "action": "Ask oleg for coffee"}]
    try:
        await trinity._execute_steps_recursive(steps)
    except Exception:
        pass

    speak_calls = [call.args for call in trinity._speak.call_args_list]

    tetyana_calls = [c[1] for c in speak_calls if c[0] == "tetyana"]
    atlas_calls = [c[1] for c in speak_calls if c[0] == "atlas"]

    # We expect:
    # 1. Tetyana: "Розпочинаю..."
    # 2. Tetyana: "What coffee?"
    # 3. Atlas: "Оскільки ви не відповіли..."
    # 4. (Attempt 2) Tetyana: "Starting attempt 2" (or nothing if dots in ID)
    # 5. (Attempt 2) Tetyana: NO "What coffee?" again because of bus_messages

    # Check for Atlas decision
    assert any("вирішив" in c for c in atlas_calls)

    # Check that Tetyana asked for coffee ONLY once
    coffee_asks = [c for c in tetyana_calls if "What coffee?" in c]
    assert len(coffee_asks) == 1


if __name__ == "__main__":
    asyncio.run(test_confirmation_flow())
