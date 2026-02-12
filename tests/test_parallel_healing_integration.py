from unittest.mock import AsyncMock, patch

import pytest

from src.brain.core.server.message_bus import MessageType
from src.brain.healing.parallel_healing import HealingStatus, parallel_healing_manager


@pytest.mark.asyncio
async def test_integration_parallel_healing_flow():
    # 1. Setup mock world
    parallel_healing_manager._tasks.clear()
    parallel_healing_manager._fixed_queue.clear()

    step_id = "test_step_99"
    error_msg = "Critical failure in database connection"

    # 2. Simulate Orchestrator submitting task
    with (
        patch(
            "src.brain.mcp.mcp_manager.mcp_manager.call_tool", new_callable=AsyncMock
        ) as mock_mcp,
        patch("src.brain.agents.grisha.Grisha") as mock_grisha_cls,
        patch(
            "src.brain.core.server.message_bus.message_bus.send", new_callable=AsyncMock
        ) as mock_send,
    ):
        # Setup Vibe analysis & fix
        mock_mcp.side_effect = [
            # 1. DevTools Analysis (Phase 1a)
            {
                "success": True,
                "analysis": {"affected_components": ["DB", "Core"]},
                "project_type": "python",
            },
            # 2. Vibe Analysis (Phase 1b)
            "Analysis: Database connection timeout. Fix: Increase timeout to 30s.",
            # 3. Vibe Sandbox (Phase 3)
            {"success": True},
        ]

        # Setup Grisha approval
        mock_grisha_inst = AsyncMock()
        mock_grisha_inst.audit_vibe_fix.return_value = {"audit_verdict": "APPROVE"}
        mock_grisha_cls.return_value = mock_grisha_inst

        # --- A. SUBMISSION ---
        task_id = await parallel_healing_manager.submit_healing_task(
            step_id=step_id,
            error=error_msg,
            step_context={"action": "connect_db"},
            log_context="logs...",
        )

        # Verify initial notification sent
        assert mock_send.call_count >= 1
        call_args = mock_send.call_args_list[0]
        msg = call_args[0][0]
        assert msg.message_type == MessageType.HEALING_STATUS
        assert msg.payload["event"] == "started"

        # --- B. EXECUTION ---
        # Wait for the background task to complete
        task = parallel_healing_manager._tasks[task_id]
        if task.asyncio_task:
            await task.asyncio_task

        assert task.status == HealingStatus.READY
        assert task.fix_description is not None and "Increase timeout" in task.fix_description

        # Verify completion notification
        assert mock_send.call_count >= 2
        last_msg = mock_send.call_args_list[-1][0][0]
        assert last_msg.message_type == MessageType.HEALING_STATUS
        assert last_msg.payload["event"] == "fix_ready"

        # Verify Monitoring DB Access
        # We need to check if monitoring_system.record_healing_event was called implicitly
        # (It uses the global instance, which is hard to mock given we imported it inside methods,
        # so for this integration test we assume it runs and maybe check the sqlite file if possible,
        # but unit test is safer for this. Let's rely on unit test for specific DB checks).

        # --- C. TETYANA DECISION ---
        # Mock Tetyana deciding to retry
        fixed_steps = await parallel_healing_manager.get_fixed_steps()
        assert len(fixed_steps) == 1
        assert fixed_steps[0].step_id == step_id

        ack_success = await parallel_healing_manager.acknowledge_fix(step_id, "retry")
        assert ack_success

        # Verify queue cleared
        fixed_steps_after = await parallel_healing_manager.get_fixed_steps()
        assert len(fixed_steps_after) == 0
        assert task.status == HealingStatus.ACKNOWLEDGED
