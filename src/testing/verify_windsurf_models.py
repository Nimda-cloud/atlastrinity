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


async def verify_windsurf_models():
    logger.info("🌊 Starting Windsurf Model Verification")

    server_name = "vibe"

    # Models extracted from src/providers/windsurf.py
    windsurf_models = [
        "deepseek-v3",
        "deepseek-r1",
        "swe-1",
        "swe-1.5",
        "grok-code-fast-1",
        "kimi-k2.5",
        "windsurf-fast",
    ]

    results = {}

    try:
        # 1. Check if Vibe is available
        logger.info("Connecting to MCP servers...")
        tools = await mcp_manager.list_tools(server_name)
        if not tools:
            logger.error("❌ Vibe server not found or no tools available.")
            return

        logger.info(f"✅ Vibe server connected. Testing {len(windsurf_models)} Windsurf models...")

        for model_alias in windsurf_models:
            logger.info(f"\n--- Testing Model: {model_alias} (Windsurf) ---")

            try:
                # Simple prompt to verify connectivity and model identity
                prompt = f"Are you working? Reply with 'Yes, I am {model_alias}'."

                logger.info(f"Sending prompt to {model_alias}...")

                # Call vibe_prompt with specific model argument
                result = await mcp_manager.call_tool(
                    server_name,
                    "vibe_prompt",
                    {"prompt": prompt, "model": model_alias, "timeout_s": 120, "args": ["--quiet"]},
                )

                # Analyze result
                content = ""
                if hasattr(result, "content") and result.content:
                    # Accessing text content effectively
                    for item in result.content:
                        if hasattr(item, "text"):
                            content += item.text + "\n"
                elif isinstance(result, dict):
                    content = str(result)
                else:
                    content = str(result)

                logger.info(f"Raw Output ({model_alias}): {content[:200]}...")

                # Try to extract the actual message content if it's JSON
                import json

                try:
                    # The output might be a JSON string inside the content
                    if isinstance(content, str):
                        # check provided content structure from previous logs
                        # It looks like: {"success": true, ..., "stdout": "{\"role\": ... }"}
                        data = json.loads(content)
                        if isinstance(data, dict) and "stdout" in data:
                            inner_stdout = data["stdout"]
                            # The stdout itself might be a JSON string of the message
                            try:
                                folder_msg = json.loads(inner_stdout)
                                if isinstance(folder_msg, dict) and "content" in folder_msg:
                                    logger.info(
                                        f"🗣️  RESPONSE ({model_alias}): {folder_msg['content'][:100]}..."
                                    )
                                else:
                                    logger.info(
                                        f"🗣️  RESPONSE ({model_alias}): {inner_stdout[:100]}..."
                                    )
                            except:
                                logger.info(f"🗣️  RESPONSE ({model_alias}): {inner_stdout[:100]}...")
                except:
                    pass

                if "error" in content.lower() and "success" not in content.lower():
                    logger.error(f"❌ {model_alias} returned error.")
                    results[model_alias] = False
                else:
                    logger.info(f"✅ {model_alias} responded.")
                    results[model_alias] = True

            except Exception as e:
                logger.error(f"💥 Exception testing {model_alias}: {e}")
                results[model_alias] = False

        logger.info("\n=== Verification Summary ===")
        for model, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            logger.info(f"Model {model}: {status}")

    except Exception as e:
        logger.error(f"Global error: {e}")
    finally:
        # cleanup if necessary, mcp_manager usually handles it
        pass


if __name__ == "__main__":
    asyncio.run(verify_windsurf_models())
