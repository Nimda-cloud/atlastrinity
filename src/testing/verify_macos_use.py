import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))


async def run_mcp_test():

    # 1. Locate Binary
    project_root = Path(__file__).parent.parent.parent
    global_cfg = Path.home() / ".config" / "atlastrinity" / "mcp" / "config.json"
    template_cfg = project_root / "config" / "mcp_servers.json.template"
    config_path = global_cfg if global_cfg.exists() else template_cfg

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    cmd_template = config["mcpServers"]["macos-use"]["command"]
    binary_path = cmd_template.replace("${PROJECT_ROOT}", str(project_root))

    if not os.path.exists(binary_path):
        return

    # 2. Start Server Process
    process = await asyncio.create_subprocess_exec(
        binary_path,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def read_response():
        if not process.stdout:
            return None
        line = await process.stdout.readline()
        if not line:
            return None
        return json.loads(line.decode())

    async def send_request(req):
        if not process.stdin:
            return
        msg = json.dumps(req) + "\n"
        process.stdin.write(msg.encode())
        await process.stdin.drain()

    # 3. Initialize
    await send_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        },
    )

    # Read init response
    while True:
        resp = await read_response()
        if not resp:
            break
        if resp.get("id") == 1:
            break

    await send_request({"jsonrpc": "2.0", "method": "notifications/initialized"})

    # 4. List Tools
    await send_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

    tools = []
    while True:
        resp = await read_response()
        if not resp:
            break
        if resp.get("id") == 2:
            tools = resp["result"]["tools"]
            for t in tools:
                pass
            break

    # 5. Test execute_command
    await send_request(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "execute_command",
                "arguments": {"command": "echo 'MCP Test Success'"},
            },
        },
    )
    while True:
        resp = await read_response()
        if not resp:
            break
        if resp.get("id") == 3:
            content = resp["result"]["content"][0]["text"]
            if "MCP Test Success" in content:
                pass
            else:
                pass
            break

    # 6. Test Screenshot
    await send_request(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "macos-use_take_screenshot", "arguments": {}},
        },
    )
    while True:
        resp = await read_response()
        if not resp:
            break
        if resp.get("id") == 4:
            if "error" in resp or resp.get("result", {}).get(
                "isError"
            ):  # Should check isError or result error
                pass
            else:
                content = resp["result"]["content"][0]["text"]
                if len(content) > 100:
                    pass
                else:
                    pass
            break

    # 7. Test Vision Analysis
    await send_request(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "macos-use_analyze_screen", "arguments": {}},
        },
    )
    while True:
        resp = await read_response()
        if not resp:
            break
        if resp.get("id") == 5:
            if resp.get("result", {}).get("isError"):
                pass
            else:
                content = resp["result"]["content"][0]["text"]
                try:
                    json.loads(content)
                except:
                    pass
            break

    # 8. SCENARIO: Calculator Automation

    # A. Open Calculator
    await send_request(
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "macos-use_open_application_and_traverse",
                "arguments": {"identifier": "Calculator"},
            },
        },
    )

    app_pid = None
    while True:
        resp = await read_response()
        if not resp:
            break
        if resp.get("id") == 10:
            content = resp["result"]["content"][0]["text"]
            try:
                res_data = json.loads(content)
                # Check for direct PID or nested in openResult
                if "pid" in res_data:
                    app_pid = res_data["pid"]
                elif "openResult" in res_data and "pid" in res_data["openResult"]:
                    app_pid = res_data["openResult"]["pid"]

                if app_pid:
                    pass
                else:
                    pass
            except:
                pass
            break

    if app_pid:
        await asyncio.sleep(1)  # Wait for animation

        # B. Type Calculation "5+5="
        await send_request(
            {
                "jsonrpc": "2.0",
                "id": 11,
                "method": "tools/call",
                "params": {
                    "name": "macos-use_type_and_traverse",
                    "arguments": {"pid": app_pid, "text": "5+5="},
                },
            },
        )
        while True:
            resp = await read_response()
            if not resp:
                break
            if resp.get("id") == 11:
                break

        await asyncio.sleep(0.5)

        # C. Take Screenshot Verification
        await send_request(
            {
                "jsonrpc": "2.0",
                "id": 12,
                "method": "tools/call",
                "params": {"name": "macos-use_take_screenshot", "arguments": {}},
            },
        )
        while True:
            resp = await read_response()
            if not resp:
                break
            if resp.get("id") == 12:
                if not resp.get("result", {}).get("isError"):
                    pass
                    # Optionally save it
                    # with open("test_calc_screen.png", "wb") as f:
                    #     content = resp["result"]["content"][0]["text"]
                    #     f.write(base64.b64decode(content))
                else:
                    pass
                break

        # D. Vision Analysis Check
        await send_request(
            {
                "jsonrpc": "2.0",
                "id": 13,
                "method": "tools/call",
                "params": {"name": "macos-use_analyze_screen", "arguments": {}},
            },
        )
        while True:
            resp = await read_response()
            if not resp:
                break
            if resp.get("id") == 13:
                if not resp.get("result", {}).get("isError"):
                    content = resp["result"]["content"][0]["text"]
                    if "10" in content:
                        pass
                    else:
                        pass
                else:
                    pass
                break

    process.terminate()


if __name__ == "__main__":
    asyncio.run(run_mcp_test())
