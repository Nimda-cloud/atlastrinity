import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.brain.logger import logger
from src.brain.mcp_manager import mcp_manager

# Configure logging
logging.basicConfig(level=logging.INFO)


async def create_desktop_script():
    logger.info("🚀 Starting Vibe Desktop Script Creation Demo")

    server_name = "vibe"
    model_alias = "deepseek-v3"  # Using DeepSeek V3 in isolated CWD to reduce prompt size
    desktop_path = os.path.expanduser("~/Desktop")
    target_file = os.path.join(desktop_path, "hello_windsurf.py")

    # Ensure Desktop exists (it should, but good practice)
    if not os.path.exists(desktop_path):
        logger.error(f"❌ Desktop path not found: {desktop_path}")
        return

    try:
        # 1. Connect to Vibe
        logger.info(f"Connecting to {server_name}...")
        tools = await mcp_manager.list_tools(server_name)
        if not tools:
            logger.error("❌ Vibe server not found.")
            return

        # 2. Construct Prompt (Simplified for Vibe)
        prompt = (
            f"Create a file at '{target_file}' with Python code that prints 'Hello Vibe!'. "
            "Just do it."
        )

        logger.info(f"Sending prompt to {model_alias} to create {target_file}...")

        # 3. Call Vibe
        result = await mcp_manager.call_tool(
            server_name,
            "vibe_prompt",
            {
                "prompt": prompt,
                "model": model_alias,
                "timeout_s": 180,
                "args": ["--quiet", "--enabled-tools", "write_file"],
            },
        )

        # 4. Log Output
        content = ""
        if hasattr(result, "content") and result.content:
            for item in result.content:
                if hasattr(item, "text"):
                    content += item.text + "\n"
        elif isinstance(result, dict):
            content = str(result)
        else:
            content = str(result)

        logger.info(f"Vibe Response: {content[:500]}...")

        # 5. Verify File Creation
        if os.path.exists(target_file):
            logger.info(f"✅ SUCCESS: File created at {target_file}")
            with open(target_file) as f:
                logger.info(f"📄 File Content:\n{f.read()}")
        else:
            logger.error(f"❌ FAILURE: File was not created at {target_file}")

    except Exception as e:
        logger.error(f"💥 Exception: {e}")
    finally:
        pass


if __name__ == "__main__":
    asyncio.run(create_desktop_script())
