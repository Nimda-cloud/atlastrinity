import asyncio
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


async def inspect_github():

    cmd = ["npx", "-y", "@modelcontextprotocol/server-github"]
    env = os.environ.copy()

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except Exception:
        return

    # We need to send initialization
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",  # Try latest
            "capabilities": {},
            "clientInfo": {"name": "atlas-inspector", "version": "1.0"},
        },
    }

    json_line = json.dumps(init_request) + "\n"

    try:
        if process.stdin:
            process.stdin.write(json_line.encode())
            await process.stdin.drain()

            # Read response
            while True:
                try:
                    assert process.stdout is not None
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
                except TimeoutError:
                    break

                if not line:
                    break

                try:
                    msg = json.loads(line.decode())
                    if msg.get("id") == 1:
                        # Send initialized notification
                        process.stdin.write(
                            json.dumps(
                                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                            ).encode()
                            + b"\n",
                        )
                        await process.stdin.drain()

                        # List tools
                        process.stdin.write(
                            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).encode()
                            + b"\n",
                        )
                        await process.stdin.drain()

                    elif msg.get("id") == 2:
                        tools = msg.get("result", {}).get("tools", [])
                        tool_names = sorted([t["name"] for t in tools])
                        for t in tool_names:
                            pass
                        break

                except json.JSONDecodeError:
                    pass

    except Exception:
        pass
    finally:
        try:
            process.terminate()
            await process.wait()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(inspect_github())
