import asyncio
import os
import sys

sys.path.append(os.getcwd())

from unittest.mock import MagicMock

# MOCK Dependencies before import
sys.modules["src.brain.monitoring"] = MagicMock()
sys.modules["src.brain.mcp_manager"] = MagicMock()

from src.brain.system_healing import HealingTask
from src.brain.tools.recovery import recovery_manager


async def test_phoenix():
    print("🦅 Testing Phoenix Protocol Simulation")

    # 1. Create a dummy snapshot to simulate previous state
    fake_state = {"messages": [], "system_state": "EXECUTING"}
    await recovery_manager.save_snapshot(
        fake_state, {"task_id": "test-123", "reason": "Test Crash"}
    )

    print("✅ Snapshot saved.")

    # 2. Simulate resuming
    snapshot = recovery_manager.load_snapshot()
    if snapshot:
        print(f"✅ Snapshot loaded: {snapshot.get('reason')}")
    else:
        print("❌ Snapshot load failed")

    # 3. Test Deep Analysis logic (Mocked Vibe)
    print("Testing Analysis Logic (Mock)...")
    try:
        # We invoke a manual analysis
        task = HealingTask("test-task", "error", "step-1")
        # In a real test, we'd mock mcp_manager, but here we just check if class instantiates
        print(f"✅ Task created: {task.task_id}")
    except Exception as e:
        print(f"❌ Analysis setup failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_phoenix())
