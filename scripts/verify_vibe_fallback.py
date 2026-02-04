import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from mcp_server import vibe_server


class TestVibeFallback(unittest.IsolatedAsyncioTestCase):
    async def test_fallback_chain_skip_openrouter(self):
        """Test skipping OpenRouter when it's unavailable."""
        mock_config = MagicMock()
        # Mock Mistral provider
        mistral_prov = MagicMock()
        mistral_prov.is_available.return_value = True

        # Mock OpenRouter provider (NOT available)
        openrouter_prov = MagicMock()
        openrouter_prov.is_available.return_value = False

        # Mock Copilot provider
        copilot_prov = MagicMock()
        copilot_prov.is_available.return_value = True

        providers = {
            "mistral": mistral_prov,
            "openrouter": openrouter_prov,
            "copilot": copilot_prov,
        }
        mock_config.get_provider.side_effect = providers.get

        mock_config.get_model_by_alias.return_value = True

        with (
            patch("mcp_server.vibe_server.get_vibe_config", return_value=mock_config),
            patch("mcp_server.vibe_server._current_model", None),
            patch("mcp_server.vibe_server._update_argv_model") as mock_update,
        ):
            # Execute
            result = await vibe_server._handle_vibe_rate_limit(
                attempt=0,
                max_retries=3,
                backoff_delays=[1, 2, 4],
                stdout="Rate limit exceeded",
                stderr="",
                argv=["vibe", "--model", "mistral-large"],
                ctx=None,
            )

            # Verification: Should have updated to gpt-4o (Copilot)
            self.assertTrue(result)
            mock_update.assert_called_with(["vibe", "--model", "mistral-large"], "gpt-4o")

    async def test_fallback_chain_use_openrouter(self):
        """Test using OpenRouter when it IS available."""
        mock_config = MagicMock()
        # Mock Mistral provider
        mistral_prov = MagicMock()
        mistral_prov.is_available.return_value = True

        # Mock OpenRouter provider (Available)
        openrouter_prov = MagicMock()
        openrouter_prov.is_available.return_value = True

        providers = {
            "mistral": mistral_prov,
            "openrouter": openrouter_prov,
        }
        mock_config.get_provider.side_effect = providers.get

        mock_config.get_model_by_alias.return_value = True

        with (
            patch("mcp_server.vibe_server.get_vibe_config", return_value=mock_config),
            patch("mcp_server.vibe_server._current_model", None),
            patch("mcp_server.vibe_server._update_argv_model") as mock_update,
        ):
            result = await vibe_server._handle_vibe_rate_limit(
                attempt=0,
                max_retries=3,
                backoff_delays=[1, 2, 4],
                stdout="Rate limit exceeded",
                stderr="",
                argv=["vibe", "--model", "mistral-large"],
                ctx=None,
            )

            self.assertTrue(result)
            mock_update.assert_called_with(
                ["vibe", "--model", "mistral-large"], "devstral-openrouter"
            )

    async def test_full_fallback_chain_mistral_to_copilot(self):
        """Test the full chain: Mistral (fail) -> OpenRouter (fail/unavail) -> Copilot (success)."""
        mock_config = MagicMock()

        # Providers
        mistral_prov = MagicMock()
        mistral_prov.is_available.return_value = True

        openrouter_prov = MagicMock()
        openrouter_prov.is_available.return_value = False  # Unavailable

        copilot_prov = MagicMock()
        copilot_prov.is_available.return_value = True

        providers = {
            "mistral": mistral_prov,
            "openrouter": openrouter_prov,
            "copilot": copilot_prov,
        }
        mock_config.get_provider.side_effect = providers.get
        mock_config.get_model_by_alias.return_value = True

        import time

        start_time = time.time()

        with (
            patch("mcp_server.vibe_server.get_vibe_config", return_value=mock_config),
            patch("mcp_server.vibe_server._current_model", None),
            patch("mcp_server.vibe_server._update_argv_model") as mock_update,
        ):
            # Execute
            result = await vibe_server._handle_vibe_rate_limit(
                attempt=0,
                max_retries=3,
                backoff_delays=[1, 2, 4],
                stdout="Rate limit exceeded",
                stderr="",
                argv=["vibe", "--model", "devstral-2"],  # Start with Mistral
                ctx=None,
            )

            duration = time.time() - start_time

            # Assertions
            self.assertTrue(result)
            # Tier 3 is Copilot (gpt-4o)
            mock_update.assert_called_with(["vibe", "--model", "devstral-2"], "gpt-4o")

            print(f"\n⚡ Fallback Speed: {duration:.4f}s")
            print("✅ Tier 3 Verification Passed: Copilot is the active fallback when others fail.")

            # Speed check: Should be sub-second since we skip unavailable providers
            self.assertLess(duration, 0.1, "Fallback should be nearly instantaneous")


if __name__ == "__main__":
    unittest.main()
