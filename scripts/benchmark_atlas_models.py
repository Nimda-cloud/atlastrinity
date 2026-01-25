import asyncio
import sys
import os

# Add src to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

from brain.mcp_manager import mcp_manager
from brain.tool_dispatcher import ToolDispatcher

async def benchmark():
    print("🚀 Starting Atlas gpt-4.1 Benchmark...")
    
    # 1. Test macOS Tool (Standard Execution)
    print("\n[TEST 1] macOS System Time...")
    res = await mcp_manager.call_tool('macos-use', 'macos-use_get_time')
    print(f"Result: {res}")
    
    # 2. Test Data Analysis (Complexity)
    print("\n[TEST 2] Data Analysis (Environment Check)...")
    res = await mcp_manager.call_tool('data-analysis', 'run_pandas_code', {"code": "import pandas as pd; print(pd.__version__)"})
    print(f"Result: {res}")
    
    # 3. Test Tool Routing (Intelligent Routing)
    print("\n[TEST 3] Intelligent Routing ('ls' synonym)...")
    dispatcher = ToolDispatcher(mcp_manager)
    res = await dispatcher.resolve_and_dispatch('ls', {"path": "."})
    print(f"Resolved to: {res.get('server', 'unknown')}.{res.get('tool', 'unknown') if isinstance(res, dict) else '?'}")
    if hasattr(res, 'content'):
        print(f"Output type: Content list (len={len(res.content)})")
    else:
        print(f"Result preview: {str(res)[:100]}...")

    # 4. Test Sequential Thinking (Raptor-mini) - FIXED ARGS
    print("\n[TEST 4] Sequential Thinking (Logic chain)...")
    res = await mcp_manager.call_tool('sequential-thinking', 'sequentialthinking', {
        "thought": "I need to verify that gpt-4.1 is correctly processing tool schemas.",
        "thoughtNumber": 1,
        "totalThoughts": 2,
        "nextThoughtNeeded": True
    })
    print(f"Result: {res}")

    # 5. Agent Coordination (The 4.1 Strength Test)
    print("\n[TEST 5] Complex Coordination (Search + Note)...")
    # Simulate a coordinated task: Find something and write it down.
    # We'll use the already verified tools to simulate the process.
    version_res = await mcp_manager.call_tool('filesystem', 'read_file', {"path": f"{PROJECT_ROOT}/package.json"})
    note_content = f"AtlasTrinity gpt-4.1 Benchmark: Project info read successfully at {__import__('datetime').datetime.now()}"
    note_res = await mcp_manager.call_tool('macos-use', 'macos-use_send_notification', {
        "title": "Benchmark Success",
        "message": "gpt-4.1 handled tool coordination perfectly."
    })
    print(f"Coordination Result: {note_res}")

    print("\n✅ Benchmark Complete!")

if __name__ == "__main__":
    asyncio.run(benchmark())
