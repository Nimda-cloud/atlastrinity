import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.mcp_server.vibe_server import _handle_vibe_rate_limit


class TestFallbackChain(unittest.IsolatedAsyncioTestCase):
    async def test_fallback_flow(self):
        # Reset state in the target module
        import src.mcp_server.vibe_server as vibe_module

        vibe_module._current_model = "gpt-4o"

        argv = ["vibe", "hello"]
        ctx = MagicMock()

        # 1. First failure (Copilot) -> Switch to Mistral
        print("\n[TEST] Simulating Copilot failure (Tier 1)...")
        result = await _handle_vibe_rate_limit(0, 3, [1, 2], "", "", argv, ctx)
        self.assertIsInstance(result, tuple)
        if isinstance(result, tuple):
            self.assertTrue(result[0])
            self.assertEqual(vibe_module._current_model, "devstral-2")

        # 2. Second failure (Mistral) -> Switch to OpenRouter
        print("[TEST] Simulating Mistral failure (Tier 2)...")
        result = await _handle_vibe_rate_limit(0, 3, [1, 2], "", "", argv, ctx)
        self.assertIsInstance(result, tuple)
        if isinstance(result, tuple):
            self.assertTrue(result[0])
            self.assertEqual(vibe_module._current_model, "devstral-openrouter")

        # 3. Third failure (OpenRouter) -> Give up
        print("[TEST] Simulating OpenRouter failure (Final)...")
        result = await _handle_vibe_rate_limit(1, 3, [1, 2], "", "", argv, ctx)
        self.assertIsInstance(result, dict)
        if isinstance(result, dict):
            self.assertFalse(result["success"])
        print(
            "[TEST] Success: Fallback chain (Copilot -> Mistral -> OpenRouter) verified via VIBE_HOME switching.\n"
        )

if __name__ == "__main__":
    unittest.main()
