
import subprocess
import json
import sys

def run_mcp_command(binary_path, method, params, request_id=1):
    process = subprocess.Popen(
        [binary_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # 1. Initialize
    init_req = {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        },
        "id": request_id
    }
    process.stdin.write(json.dumps(init_req) + "\n")
    process.stdin.flush()
    
    # Read init response
    line = process.stdout.readline()
    # print(f"Init Response: {line}", file=sys.stderr)

    # 2. Call Tool
    tool_req = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": method,
            "arguments": params
        },
        "id": request_id + 1
    }
    process.stdin.write(json.dumps(tool_req) + "\n")
    process.stdin.flush()

    # Read tool response
    line = process.stdout.readline()
    print(line)

    process.terminate()

if __name__ == "__main__":
    binary = "/Users/dev/Documents/GitHub/atlastrinity/vendor/mcp-server-macos-use/.build/release/mcp-server-macos-use"
    # Try to open Calculator
    run_mcp_command(binary, "macos-use_open_application_and_traverse", {"identifier": "Calculator"})
