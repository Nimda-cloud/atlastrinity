import asyncio
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.watchdog import watchdog


async def test():
    print("Starting Watchdog reconciliation...")
    await watchdog.reconcile_processes()
    status = watchdog.get_status()
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
