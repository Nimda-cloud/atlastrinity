import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))


async def test_vibe_prompt_fallback():
    print("🧪 Testing Vibe MCP Tools (vibe_prompt) for Fallback Integration")
    from mcp_server import vibe_server

    # Sabotage providers to force fallback
    from mcp_server.vibe_config import ApiStyle, Backend, ProviderConfig

    # Mock context
    mock_ctx = MagicMock()
    mock_ctx.log = AsyncMock()

    from unittest.mock import patch

    with patch("mcp_server.vibe_server.is_network_available", return_value=True):
        # 1. Get real config
        from mcp_server.vibe_server import get_vibe_config

        config = get_vibe_config()

        # 2. Manually override providers list to avoid complex mocking issues
        config.providers = [
            ProviderConfig(
                name="mistral",
                api_base="http://fail",
                api_key_env_var="FAIL_MISTRAL",
                api_style=ApiStyle.MISTRAL,
                backend=Backend.MISTRAL,
            ),
            ProviderConfig(
                name="openrouter",
                api_base="http://fail",
                api_key_env_var="FAIL_OPENROUTER",
                api_style=ApiStyle.OPENAI,
                backend=Backend.GENERIC,
            ),
            ProviderConfig(
                name="copilot",
                api_base="http://127.0.0.1:8085",
                api_key_env_var="COPILOT_SESSION_TOKEN",
                api_style=ApiStyle.OPENAI,
                backend=Backend.GENERIC,
            ),
        ]

        # 3. Inject this specific instance
        with patch("mcp_server.vibe_server.get_vibe_config", return_value=config):
            print("🔧 Calling vibe_prompt with Tier 3 (gpt-4o) directly...")

            try:
                # We use a simple prompt
                result = await vibe_server.vibe_prompt(
                    ctx=mock_ctx,
                    prompt="Say 'Direct Success'",
                    model="gpt-4o",  # Start directly with Copilot
                    timeout_s=30,
                )
                print("\n✅ Verification Result:")
                print(f"Success: {result.get('success')}")
                if result.get("error"):
                    print(f"Error: {result.get('error')}")

                # Print logs emitted to context
                print("\n📝 MCP Logs emitted:")
                for call in mock_ctx.log.call_args_list:
                    print(f"  [{call[0][0].upper()}] {call[0][1]}")
            except Exception as e:
                print(f"❌ Test crashed during vibe_prompt: {e}")
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_vibe_prompt_fallback())
