import unittest

from src.brain.core.orchestration.error_router import (  # Adjust import based on actual structure
    error_router,
)


class TestErrorLoop(unittest.TestCase):
    def test_help_pending_escalation(self):
        """Verify that 'help_pending' escalates to ASK_USER after 3 attempts"""

        # simulated error string
        error_msg = "help_pending"

        # Attempt 1: Should be ATLAS_PLAN (standard discovery)
        strategy_1 = error_router.decide(error_msg, attempt=1)
        print(f"Attempt 1 Action: {strategy_1.action}")
        self.assertEqual(strategy_1.action, "ATLAS_PLAN")

        # Attempt 3: Should still be ATLAS_PLAN
        strategy_3 = error_router.decide(error_msg, attempt=3)
        print(f"Attempt 3 Action: {strategy_3.action}")
        self.assertEqual(strategy_3.action, "ATLAS_PLAN")

        # Attempt 4: Should be ASK_USER (Breaking the loop)
        strategy_4 = error_router.decide(error_msg, attempt=4)
        print(f"Attempt 4 Action: {strategy_4.action}")
        self.assertEqual(strategy_4.action, "ASK_USER")
        print("SUCCESS: Loop break verified.")


if __name__ == "__main__":
    unittest.main()
