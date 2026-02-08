from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.brain.constraint_monitor import ConstraintMonitor, constraint_monitor
from src.brain.parallel_healing import HealingStatus, parallel_healing_manager


@pytest.mark.asyncio
async def test_constraint_monitor_violations():
    # 1. Setup
    monitor = ConstraintMonitor()

    with (
        patch.object(monitor, "_read_constraints", return_value=["No errors in output"]),
        patch("src.brain.mcp_manager.mcp_manager.call_tool", new_callable=AsyncMock) as mock_mcp,
        patch(
            "src.brain.parallel_healing.parallel_healing_manager.submit_healing_task",
            new_callable=AsyncMock,
        ) as mock_submit,
    ):
        # Mock Vibe returning a violation
        mock_mcp.return_value = "VIOLATION: Error found in output\nEVIDENCE: 'Error: timeout'"

        # 2. Execute
        await monitor.check_compliance("log1\nlog2", [{"message": "log1"}, {"message": "log2"}])

        # 3. Verify
        mock_mcp.assert_called_once()
        mock_submit.assert_called_once()

        # Verify priority is 2 (High)
        call_kwargs = mock_submit.call_args.kwargs
        assert call_kwargs["priority"] == 2
        assert "User Constraint Violation" in call_kwargs["error"]


@pytest.mark.asyncio
async def test_constraint_monitor_compliant():
    monitor = ConstraintMonitor()

    with (
        patch.object(monitor, "_read_constraints", return_value=["No errors"]),
        patch("src.brain.mcp_manager.mcp_manager.call_tool", new_callable=AsyncMock) as mock_mcp,
        patch(
            "src.brain.parallel_healing.parallel_healing_manager.submit_healing_task",
            new_callable=AsyncMock,
        ) as mock_submit,
    ):
        mock_mcp.return_value = "COMPLIANT"

        await monitor.check_compliance("logs...", [{"message": "log"}])

        mock_submit.assert_not_called()
