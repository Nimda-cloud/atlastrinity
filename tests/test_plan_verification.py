import asyncio
from unittest.mock import AsyncMock

import pytest

from src.brain.agents.atlas import TaskPlan
from src.brain.agents.grisha import Grisha


def test_grisha_verifies_safe_plan():
    async def run_test():
        # Setup
        grisha = Grisha()
        # Mock LLM for strategy/verdict
        grisha.strategist = AsyncMock()
        grisha.strategist.ainvoke.return_value = "APPROVE: The plan is safe and logical."

        plan = TaskPlan(
            id="test_plan",
            goal="Test Goal",
            steps=[{"action": "echo 'Hello World'", "voice_action": "Printing hello"}],
        )

        # Execute
        result = await grisha.verify_plan(plan, "User wants to print hello")

        # Verify
        assert result.verified is True
        assert result.confidence >= 0.9
        assert "Printing hello" in str(grisha.strategist.ainvoke.call_args)

    asyncio.run(run_test())


def test_grisha_rejects_unsafe_plan():
    async def run_test():
        # Setup
        grisha = Grisha()
        grisha.strategist = AsyncMock()
        grisha.strategist.ainvoke.return_value = "REJECT: The plan contains dangerous commands."

        plan = TaskPlan(
            id="unsafe_plan",
            goal="Destroy System",
            steps=[{"action": "rm -rf /", "voice_action": "Deleting everything"}],
        )

        # Execute
        result = await grisha.verify_plan(plan, "User wants to clean up")

        # Verify
        assert result.verified is False
        assert result.issues is not None
        assert len(result.issues) > 0

    asyncio.run(run_test())
def test_grisha_approves_creator_request():
    async def run_test():
        # Setup
        grisha = Grisha()
        grisha.strategist = AsyncMock()
        # Simulate a rejection due to authorization that should be overridden
        grisha.strategist.ainvoke.return_value = "REJECT: Lack of written authorization for pentest."
        
        plan = TaskPlan(
            id="pentest_plan",
            goal="Test network",
            steps=[{"action": "aircrack-ng", "voice_action": "Scanning"}]
        )
        
        # Execute with Creator mention
        result = await grisha.verify_plan(plan, "Олег Миколайович asks to test Zub1")
        
        # Verify override
        assert result.verified is True
        assert "Творцем" in result.voice_message

    asyncio.run(run_test())
