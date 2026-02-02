from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.brain.parallel_healing import HealingStatus, HealingTask, ParallelHealingManager


@pytest.fixture
def manager():
    with patch("src.brain.state_manager.state_manager.available", False):
        mgr = ParallelHealingManager()
        return mgr

@pytest.mark.asyncio
async def test_submit_healing_task(manager):
    # Mock dependencies
    with patch("src.brain.parallel_healing.asyncio.create_task") as mock_create_task, \
         patch.object(manager, "_notify_healing_started") as mock_notify:
        
        task_id = await manager.submit_healing_task(
            step_id="step_1",
            error="Test error",
            step_context={"action": "test"},
            log_context="log1\nlog2"
        )
        
        assert task_id.startswith("heal_step_1_")
        assert task_id in manager._tasks
        task = manager._tasks[task_id]
        assert task.step_id == "step_1"
        assert task.status == HealingStatus.PENDING
        
        mock_create_task.assert_called_once()
        mock_notify.assert_called_once_with(task)

@pytest.mark.asyncio
async def test_max_concurrent_tasks(manager):
    # Fill up tasks
    manager._max_concurrent = 2
    
    # Create 2 mock active tasks
    t1 = HealingTask("t1", "s1", "err", {}, "", status=HealingStatus.ANALYZING)
    t2 = HealingTask("t2", "s2", "err", {}, "", status=HealingStatus.FIXING)
    manager._tasks["t1"] = t1
    manager._tasks["t2"] = t2
    
    # Try to add 3rd
    with pytest.raises(RuntimeError, match="Max concurrent healing tasks reached"):
        await manager.submit_healing_task("s3", "err", {}, "")

@pytest.mark.asyncio
async def test_acknowledge_fix(manager):
    # Setup fixed queue
    from src.brain.parallel_healing import FixedStepInfo
    
    fix = FixedStepInfo(
        task_id="t1",
        step_id="s1",
        fix_description="Fixed it",
        fixed_at=datetime.now(),
        grisha_verdict={}
    )
    manager._fixed_queue.append(fix)
    
    # Mock task
    t1 = HealingTask("t1", "s1", "err", {}, "", status=HealingStatus.READY)
    manager._tasks["t1"] = t1
    
    # Act
    result = await manager.acknowledge_fix("s1", "retry")
    
    # Assert
    assert result is True
    assert len(manager._fixed_queue) == 0
    assert t1.status == HealingStatus.ACKNOWLEDGED

@pytest.mark.asyncio
async def test_run_healing_workflow_success(manager):
    task = HealingTask("t1", "s1", "err", {}, "")
    manager._tasks["t1"] = task
    
    # Mock all the external calls
    with patch("src.brain.mcp_manager.mcp_manager.call_tool", new_callable=AsyncMock) as mock_mcp, \
         patch("src.brain.agents.grisha.Grisha") as mock_grisha_cls, \
         patch.object(manager, "_notify_fix_ready", new_callable=AsyncMock) as mock_notify, \
         patch.object(manager, "_test_in_sandbox", new_callable=AsyncMock) as mock_sandbox:
         
        # Setup mocks
        mock_mcp.return_value = "Fix: Use the foo bar"
        mock_sandbox.return_value = {"success": True}
        
        mock_grisha = AsyncMock()
        mock_grisha.audit_vibe_fix.return_value = {"audit_verdict": "APPROVE"}
        mock_grisha_cls.return_value = mock_grisha
        
        # Run workflow
        await manager._run_healing_workflow(task)
        
        assert task.status == HealingStatus.READY
        assert task.fix_description is not None and "Use the foo bar" in task.fix_description
        assert len(manager._fixed_queue) == 1
        mock_notify.assert_called_once()

@pytest.mark.asyncio
async def test_run_healing_workflow_grisha_reject(manager):
    task = HealingTask("t1", "s1", "err", {}, "")
    manager._tasks["t1"] = task
    
    with patch("src.brain.mcp_manager.mcp_manager.call_tool", new_callable=AsyncMock) as mock_mcp, \
         patch("src.brain.agents.grisha.Grisha") as mock_grisha_cls, \
         patch.object(manager, "_test_in_sandbox", new_callable=AsyncMock) as mock_sandbox:
         
        mock_mcp.return_value = "Fix: Bad code"
        mock_sandbox.return_value = {"success": True}
        
        mock_grisha = AsyncMock()
        mock_grisha.audit_vibe_fix.return_value = {"audit_verdict": "REJECT", "reasoning": "Unsafe"}
        mock_grisha_cls.return_value = mock_grisha
        
        await manager._run_healing_workflow(task)
        
        assert task.status == HealingStatus.FAILED
        assert task.error_message is not None and "Grisha rejected" in task.error_message
        assert len(manager._fixed_queue) == 0
