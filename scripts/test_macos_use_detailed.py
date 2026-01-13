
import subprocess
import json
import sys
import time

def run_mcp_command(binary_path, commands):
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
        "id": 0
    }
    process.stdin.write(json.dumps(init_req) + "\n")
    process.stdin.flush()
    process.stdout.readline() # Consume init response

    results = []
    for i, (method, params) in enumerate(commands):
        tool_req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": method,
                "arguments": params
            },
            "id": i + 1
        }
        process.stdin.write(json.dumps(tool_req) + "\n")
        process.stdin.flush()
        line = process.stdout.readline()
        results.append(line)
        time.sleep(1) # Give it a second

    process.terminate()
    return results

if __name__ == "__main__":
    binary = "/Users/dev/Documents/GitHub/atlastrinity/vendor/mcp-server-macos-use/.build/release/mcp-server-macos-use"
    
    # Task: Open Safari, type a search query
    commands = [
        ("macos-use_open_application_and_traverse", {"identifier": "Safari"}),
    ]
    
    results = run_mcp_command(binary, commands)
    for res in results:
        try:
            parsed = json.loads(res)
            # The tool result text is a JSON string itself
            tool_result_text = parsed['result']['content'][0]['text']
            tool_result = json.loads(tool_result_text)
            print(f"Tool Result Summary: {tool_result.keys()}")
            if 'traversalAfter' in tool_result:
                print(f"Traversal items count: {len(tool_result['traversalAfter'])}")
                # Print first few items to see structure
                for item in tool_result['traversalAfter'][:5]:
                    print(f" - {item.get('role', 'N/A')}: {item.get('title', 'N/A')} (id: {item.get('identifier', 'N/A')})")
            else:
                print("No traversalAfter found in result.")
        except Exception as e:
            print(f"Error parsing result: {e}")
            print(res)
