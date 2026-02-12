import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".config/atlastrinity/mcp/config.json"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


async def run_mcp_server(name: str, config: dict[str, Any]) -> bool:

    cmd = config.get("command")
    args = config.get("args", [])
    env = config.get("env", {})
    passed = False

    # Resolve placeholders
    if cmd is None:
        return False

    if cmd == "python3":
        cmd = sys.executable
    if "${PROJECT_ROOT}" in cmd:
        cmd = cmd.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))

    # Check if disabled
    if config.get("disabled", False):
        return True

    full_cmd: list[str] = [cmd] + [
        (arg or "")
        .replace("${HOME}", str(Path.home()))
        .replace("${PROJECT_ROOT}", str(PROJECT_ROOT))
        .replace("${GITHUB_TOKEN}", os.environ.get("GITHUB_TOKEN", ""))
        for arg in args
    ]

    # Prepare env
    run_env = os.environ.copy()
    run_env.update(env)

    try:
        process = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=run_env,
        )
    except Exception:
        return False

    async def read_stream(stream, label):
        while True:
            line = await stream.readline()
            if not line:
                break
            # print(f"[{label}] {line.decode().strip()}")

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
        if process.stdin and process.stdout:
            process.stdin.write(json_line.encode())
            await process.stdin.drain()

            # Read response
            while True:
                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)
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
                        [t["name"] for t in tools]
                        passed = True
                        break

                    # Some servers act as clients too or send notifications, ignore those
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

    return passed


async def main():
    if not CONFIG_PATH.exists():
        return

    with open(CONFIG_PATH) as f:
        data = json.load(f)

    servers = data.get("mcpServers", {})
    results = {}

    for name, config in servers.items():
        if name.startswith("_"):
            continue
        results[name] = await run_mcp_server(name, config)

    for _, _ in results.items():
        pass


if __name__ == "__main__":
    asyncio.run(main())
