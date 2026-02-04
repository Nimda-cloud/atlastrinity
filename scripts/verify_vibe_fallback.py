
import asyncio

# Add src to path to import vibe_server
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from mcp_server import vibe_server


class TestVibeFallback(unittest.IsolatedAsyncioTestCase):
    async def test_fallback_chain_skip_openrouter(self):
        """Test that we skip OpenRouter if it's not available and go straight to Copilot."""
        
        # Mock Context
        ctx = AsyncMock()
        
        # Mock Config
        mock_config = MagicMock()
        
        # Scenario: Mistral failed (attempt 0), Current model is None
        # OpenRouter is NOT available
        # Copilot IS available
        
        mock_openrouter_provider = MagicMock()
        mock_openrouter_provider.is_available.return_value = False
        
        mock_copilot_provider = MagicMock()
        mock_copilot_provider.is_available.return_value = True
        
        def get_provider_side_effect(name):
            if name == 'openrouter':
                return mock_openrouter_provider
            if name == 'copilot':
                return mock_copilot_provider
            return None
            
        mock_config.get_provider.side_effect = get_provider_side_effect
        
        # Mock connection to vibe_server's global config
        with patch('mcp_server.vibe_server.get_vibe_config', return_value=mock_config):
            # inject mocks for _current_model and _update_argv_model
            with patch('mcp_server.vibe_server._current_model', None):
                with patch('mcp_server.vibe_server._update_argv_model') as mock_update:
                    
                    # Execute
                    # We simulate attempt 0 (first failure)
                    result = await vibe_server._handle_vibe_rate_limit(
                        attempt=0,
                        max_retries=3,
                        backoff_delays=[1],
                        stdout="",
                        stderr="Rate limit exceeded",
                        argv=["vibe", "--model", "mistral-large"],
                        ctx=ctx
                    )
                    
                    # Assertions
                    # Should return True (retry initiated)
                    self.assertTrue(result, "Should return True to signal retry")
                    
                    # Should have switched to Copilot (gpt-4o), SKIPPING OpenRouter
                    # We expect _update_argv_model to be called with 'gpt-4o'
                    mock_update.assert_called_with(["vibe", "--model", "mistral-large"], "gpt-4o")
                    
                    print("\n✅ Verification Passed: Skipped unavailable OpenRouter and picked Copilot.")

    async def test_fallback_chain_use_openrouter(self):
        """Test that we use OpenRouter if it IS available."""
        
        ctx = AsyncMock()
        mock_config = MagicMock()
        
        # OpenRouter IS available
        mock_openrouter_provider = MagicMock()
        mock_openrouter_provider.is_available.return_value = True
        
        mock_config.get_provider.return_value = mock_openrouter_provider
        # We also need get_model_by_alias to return something truthy for 'devstral-openrouter'
        mock_config.get_model_by_alias.return_value = True
        
        with patch('mcp_server.vibe_server.get_vibe_config', return_value=mock_config):
            with patch('mcp_server.vibe_server._current_model', None):
                with patch('mcp_server.vibe_server._update_argv_model') as mock_update:
                    
                    result = await vibe_server._handle_vibe_rate_limit(
                        attempt=0,
                        max_retries=3,
                        backoff_delays=[1],
                        stdout="",
                        stderr="Rate limit exceeded",
                        argv=["vibe"],
                        ctx=ctx
                    )
                    
                    self.assertTrue(result)
                    # Should have switched to OpenRouter
                    mock_update.assert_called_with(["vibe"], "devstral-openrouter")
                    print("\n✅ Verification Passed: Used available OpenRouter.")

if __name__ == '__main__':
    unittest.main()
