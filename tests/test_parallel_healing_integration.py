
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.brain.parallel_healing import parallel_healing_manager, HealingStatus
from src.brain.message_bus import message_bus, MessageType, AgentMsg

@pytest.mark.asyncio
async def test_integration_parallel_healing_flow():
    # 1. Setup mock world
    parallel_healing_manager._tasks.clear()
    parallel_healing_manager._fixed_queue.clear()
    
    step_id = "test_step_99"
    error_msg = "Critical failure in database connection"
    
    # 2. Simulate Orchestrator submitting task
    with patch("src.brain.mcp_manager.mcp_manager.call_tool", new_callable=AsyncMock) as mock_mcp, \
         patch("src.brain.agents.grisha.Grisha") as mock_grisha_cls, \
         patch("src.brain.message_bus.message_bus.send", new_callable=AsyncMock) as mock_send:
            
        # Setup Vibe analysis & fix
        mock_mcp.side_effect = [
            "Analysis: Database connection timeout. Fix: Increase timeout to 30s.", # vibe_analyze_error result
            {"success": True} # vibe_test_in_sandbox result
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
            log_context="logs..."
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
        await task.asyncio_task
        
        assert task.status == HealingStatus.READY
        assert "Increase timeout" in task.fix_description
        
        # Verify completion notification
        assert mock_send.call_count >= 2
        last_msg = mock_send.call_args_list[-1][0][0]
        assert last_msg.message_type == MessageType.HEALING_STATUS
        assert last_msg.payload["event"] == "fix_ready"
        assert last_msg.to_agent == "tetyana"
        
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
