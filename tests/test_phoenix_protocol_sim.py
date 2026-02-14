import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Mocking parts of the system for simulation if Redis/DB is not available
class MockRedis:
    def __init__(self):
        self.data = {}

    async def set(self, key, value):
        self.data[key] = value

    async def get(self, key):
        return self.data.get(key)

    async def delete(self, key):
        if key in self.data:
            del self.data[key]

    async def keys(self, pattern):
        import fnmatch

        return [k for k in self.data if fnmatch.fnmatch(k, pattern)]


async def test_phoenix_cycle_sim():
    print("--- Testing Phoenix Protocol (Restart & Resume) Simulation ---")

    # 1. Setup Mock State Manager
    from src.brain.core.services.state_manager import StateManager

    sm = StateManager()
    mock_redis = MockRedis()
    sm.redis_client = mock_redis
    sm.available = True
    sm.prefix = "atlastrinity_test"

    session_id = "test_session_123"
    test_state = {
        "messages": [],
        "system_state": "EXECUTING",
        "current_plan": {"steps": [{"id": "1", "action": "test"}]},
        "session_id": session_id,
    }

    # 2. Simulate RESTART strategy trigger (the bug I fixed)
    print("Simulating RESTART trigger...")
    # This is what _handle_strategy_restart does:
    await sm.save_session(session_id, test_state)

    reason = "State corruption simulation"
    meta = {"reason": reason, "timestamp": datetime.now().isoformat()}
    restart_key = sm._key("restart_pending")
    await sm.redis_client.set(restart_key, json.dumps(meta))

    print(f"State saved to Redis with key: {sm._key(f'session:{session_id}')}")
    print(f"Restart flag set with key: {restart_key}")

    # 3. Verify restart flag exists and has prefix
    assert restart_key == "atlastrinity_test:restart_pending"
    stored_meta = await sm.redis_client.get(restart_key)
    assert stored_meta is not None
    assert reason in stored_meta
    print("✅ RESTART state preservation verified (with prefix)!")

    # 4. Simulate Resume Logic (_resume_after_restart)
    print("\nSimulating system resume after 'restart'...")

    # Mock Orchestrator part
    class MockOrchestrator:
        def __init__(self):
            self.state = {}
            self.current_session_id = None
            self._resumption_pending = False

    orch = MockOrchestrator()

    # Logic from _resume_after_restart:
    data = await sm.redis_client.get(restart_key)
    if data:
        json.loads(data)
        # In real code it might use 'last_session' if session_id is missing
        last_session = await sm.redis_client.get(sm._key("last_session"))

        saved_state = await sm.restore_session(last_session)
        if saved_state:
            orch.state = saved_state
            orch.current_session_id = last_session
            await sm.redis_client.delete(restart_key)
            orch._resumption_pending = True

    # 5. Verify Resumption
    assert orch._resumption_pending is True
    assert orch.current_session_id == session_id
    assert orch.state["system_state"] == "EXECUTING"

    # Verify flag cleared
    final_flag = await sm.redis_client.get(restart_key)
    assert final_flag is None

    print("✅ Phoenix Resume logic verified!")
    print("\n✨ Phoenix Protocol verification PASSED!")


if __name__ == "__main__":
    asyncio.run(test_phoenix_cycle_sim())
