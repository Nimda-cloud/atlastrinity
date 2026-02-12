import asyncio
import logging
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.mcp_server.vibe_server import (
    vibe_ask,
    vibe_code_review,
    vibe_get_config,
    vibe_implement_feature,
    vibe_smart_plan,
    vibe_test_in_sandbox,
    vibe_which,
)

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_vibe")


class MockContext:
    def __init__(self):
        self.request_id = "test-req"
        self.client_id = "test-client"
        self.log = AsyncMock()

        # Side effect to print logs
        async def log_side_effect(level, message, logger_name=""):
            pass

        self.log.side_effect = log_side_effect


async def run_test():
    logger.info("--- STARTING VIBE MCP FULL TEST ---")
    ctx = MockContext()

    # 1. Check Configuration
    logger.info("1. Testing vibe_get_config...")
    config_res = await vibe_get_config(ctx)
    if not config_res["success"]:
        logger.error(f"Config check failed: {config_res}")
        return
    logger.info(f"Active Model: {config_res['active_model']}")
    logger.info(f"Mode: {config_res['mode']}")

    # 2. Check Binary
    logger.info("\n2. Testing vibe_which...")
    which_res = await vibe_which(ctx)
    logger.info(f"Vibe Binary: {which_res.get('binary')}")
    logger.info(f"Vibe Version: {which_res.get('version')}")

    # 3. Smart Plan
    logger.info("\n3. Testing vibe_smart_plan...")
    await vibe_smart_plan(
        ctx,
        objective="Create a Python script that calculates the Fibonacci sequence up to N terms, and a corresponding unit test.",
        model="gpt-4o",
    )
    logger.info("Plan generated successfully (content truncated for brevity)")
    # print(plan_res)

    # 4. Implement Feature
    logger.info("\n4. Testing vibe_implement_feature (Fibonacci Generator)...")
    # Clean previous run
    if os.path.exists("fib_app.py"):
        os.remove("fib_app.py")
    if os.path.exists("test_fib_app.py"):
        os.remove("test_fib_app.py")

    impl_res = await vibe_implement_feature(
        ctx,
        goal="Create a Python file 'fib_app.py' with a function 'fibonacci(n)' and a 'main' block. Also create 'test_fib_app.py' using unittest.",
        cwd=os.getcwd(),
        quality_checks=True,
        iterative_review=False,  # Speed up test
        model="gpt-4o",
    )

    if impl_res.get("success"):
        logger.info("Implementation successful!")
    else:
        logger.error(f"Implementation failed: {impl_res}")

    # Verify files exist
    if os.path.exists("fib_app.py"):
        logger.info("✅ fib_app.py created")
        with open("fib_app.py") as f:
            pass
    else:
        logger.error("❌ fib_app.py MISSING")

    # 5. Code Review
    logger.info("\n5. Testing vibe_code_review...")
    if os.path.exists("fib_app.py"):
        await vibe_code_review(ctx, "fib_app.py", focus_areas="performance")
        logger.info("Review completed")
        # print(review_res)

    # 6. Sandbox Test
    logger.info("\n6. Testing vibe_test_in_sandbox...")
    if os.path.exists("test_fib_app.py"):
        # We need to read the files to pass them to sandbox
        with open("fib_app.py") as f:
            fib_code = f.read()
        with open("test_fib_app.py") as f:
            test_code = f.read()

        sandbox_res = await vibe_test_in_sandbox(
            ctx,
            test_script=test_code,
            target_files={"fib_app.py": fib_code},
            command="python3 vibe_test_runner.py",
        )
        logger.info(f"Sandbox Result: {'✅ PASS' if sandbox_res['success'] else '❌ FAIL'}")
        logger.info(f"Sandbox Output: {sandbox_res.get('stdout', '')[:200]}...")

    # 7. Ask (Quick Question)
    logger.info("\n7. Testing vibe_ask...")
    ask_res = await vibe_ask(
        ctx, "What is the time complexity of a recursive fibonacci function?", model="gpt-4o"
    )
    # The response is usually in parsed_response or stdout
    answer = ask_res.get("parsed_response") or ask_res.get("stdout")
    logger.info(f"Answer received: {str(answer)[:100]}...")

    logger.info("\n--- TEST COMPLETE ---")


if __name__ == "__main__":
    asyncio.run(run_test())
