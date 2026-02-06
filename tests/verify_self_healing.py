import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path

# Setup mocking for Orchestrator/Vibe context
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SelfHealingTest")

from src.brain.tools.recovery import recovery_manager
from src.brain.tools.sandbox_runner import sandbox_runner


async def test_self_healing_logic():
    """
    Simulates the specific steps of the Self-Healing "Phoenix Protocol":
    1. A 'broken' file exists.
    2. Sandbox verification is requested for a 'fix'.
    3. Recovery snapshot is saved.
    4. Recovery snapshot is loaded (simulating restart).
    """
    print("\n--- Starting Self-Healing Verification ---")

    # SETUP: Create a fake workspace with a broken file
    with tempfile.TemporaryDirectory() as temp_workspace:
        workspace_path = Path(temp_workspace)
        sandbox_runner.workspace_root = workspace_path  # Override for test

        # 1. Create 'broken.py' that fails validation
        broken_file = workspace_path / "broken.py"
        broken_file.write_text("def add(a, b): return a - b  # BUG: should be +")

        # 2. Create 'verify_math.py' that expects correct math
        verify_script = workspace_path / "verify_math.py"
        verify_script.write_text("""
import sys
from broken import add

if add(2, 2) == 4:
    print("Verification Passed")
    sys.exit(0)
else:
    print("Verification Failed")
    sys.exit(1)
""")

        # TEST PHASE 1: Verify the BROKEN state fails in sandbox
        print("\n[Test 1] Verifying broken state fails in sandbox...")
        sandbox_dir = sandbox_runner.prepare_sandbox(str(broken_file), str(verify_script))
        success, out, err = sandbox_runner.run_verification(sandbox_dir, "verify_math.py")

        if not success:
            print("✅ Success: Sandbox correctly identified code is broken.")
        else:
            print("❌ Failure: Sandbox passed broken code!", out)
            return

        # TEST PHASE 2: Apply FIX in sandbox and verify PASS
        print("\n[Test 2] Applying fix in sandbox and verifying...")
        # Simulate Apply Patch: Modify the file IN THE SANDBOX
        sandboxed_broken = Path(sandbox_dir) / "broken.py"
        sandboxed_broken.write_text("def add(a, b): return a + b  # FIXED")

        success_fix, out_fix, err_fix = sandbox_runner.run_verification(
            sandbox_dir, "verify_math.py"
        )

        if success_fix:
            print("✅ Success: Sandbox verified the fix.")
        else:
            print("❌ Failure: Sandbox rejected the fix!", out_fix, err_fix)
            return

        # TEST PHASE 3: Recovery Snapshot
        print("\n[Test 3] Testing State Preservation (Phoenix Protocol)...")
        fake_state = {"current_step": "fix_math_bug", "memory": "test_memory"}
        fake_context = {"session_id": "session_123", "task_id": "task_abc", "reason": "Testing"}

        saved = await recovery_manager.save_snapshot(fake_state, fake_context)
        if saved:
            print("✅ Success: Snapshot saved.")
        else:
            print("❌ Failure: Could not save snapshot.")
            return

        # TEST PHASE 4: Load Snapshot
        loaded_data = recovery_manager.load_snapshot()
        if loaded_data and loaded_data["session_id"] == "session_123":
            print(f"✅ Success: Loaded snapshot correctly. Timestamp: {loaded_data['timestamp']}")
        else:
            print("❌ Failure: Snapshot load mismatch or missing.", loaded_data)
            return

        # Cleanup
        recovery_manager.clear_snapshot()
        print("\n🎉 ALL SYSTEMS GO: Self-Healing Logic Verified.")


if __name__ == "__main__":
    asyncio.run(test_self_healing_logic())
