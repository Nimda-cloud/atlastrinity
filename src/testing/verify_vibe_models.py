import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.brain.logger import logger
from src.brain.mcp_manager import mcp_manager

# Configure logging
logging.basicConfig(level=logging.INFO)


async def verify_models():
    logger.info("🧪 Starting Vibe Model Verification")

    server_name = "vibe"
    models_to_test = [
        {"alias": "gpt-4.1", "provider": "Copilot"},
        {"alias": "deepseek-v3", "provider": "Windsurf"},
    ]

    results = {}

    try:
        # 1. Initialize MCP Manager (connects to servers)
        logger.info("Connecting to MCP servers...")
        # valid mcp_manager usage does not require explicit initialize

        # 2. Check if Vibe is available
        tools = await mcp_manager.list_tools(server_name)
        if not tools:
            logger.error("❌ Vibe server not found or no tools available.")
            return

        logger.info(f"✅ Vibe server connected. Testing {len(models_to_test)} models...")

        for model in models_to_test:
            alias = model["alias"]
            provider = model["provider"]
            logger.info(f"\n--- Testing Model: {alias} ({provider}) ---")

            try:
                # Use a simple prompt.
                # We use specific keywords to verify the model is actually responding intelligibly.
                prompt = f"Are you working? Reply with 'Yes, I am {alias}'."

                # Call vibe_prompt with specific model argument
                # The server should handle proxy startup automatically.
                logger.info(f"Sending prompt to {alias}...")
                result = await mcp_manager.call_tool(
                    server_name,
                    "vibe_prompt",
                    {
                        "prompt": prompt,
                        "model": alias,
                        "timeout_s": 120,  # Give enough time for proxy startup
                        "args": ["--quiet"],  # Minimal output
                    },
                )

                # Analyze result
                content = ""
                if hasattr(result, "content") and result.content:
                    content = result.content[0].text
                elif isinstance(result, dict):
                    content = str(result)
                elif hasattr(result, "output"):  # Some MCP implementations
                    content = str(result.output)
                else:
                    content = str(result)

                logger.info(f"Raw Output ({alias}): {content[:200]}...")  # Log first 200 chars

                if "error" in content.lower() and "success" not in content.lower():
                    logger.error(f"❌ {alias} returned error.")
                    results[alias] = False
                else:
                    logger.info(f"✅ {alias} responded.")
                    results[alias] = True

            except Exception as e:
                logger.error(f"💥 Exception testing {alias}: {e}")
                results[alias] = False

        logger.info("\n=== Verification Summary ===")
        for model, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"Model {model}: {status}")

    except Exception as e:
        logger.error(f"Global error: {e}")
    finally:
        await mcp_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(verify_models())
