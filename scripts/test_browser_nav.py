
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

    def send_req(method, params, req_id):
        req = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": req_id
        }
        process.stdin.write(json.dumps(req) + "\n")
        process.stdin.flush()
        return process.stdout.readline()

    # 1. Initialize
    send_req("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0"}
    }, 0)

    results = []
    pid = None
    for i, (method, params) in enumerate(commands):
        if "pid" in params and pid:
            params["pid"] = pid
            
        res_line = send_req("tools/call", {"name": method, "arguments": params}, i + 1)
        results.append(res_line)
        
        # Extract PID if available
        try:
            parsed = json.loads(res_line)
            tool_result_text = parsed['result']['content'][0]['text']
            tool_result = json.loads(tool_result_text)
            if 'openResult' in tool_result:
                pid = tool_result['openResult']['pid']
            elif 'traversalPid' in tool_result:
                pid = tool_result['traversalPid']
        except:
            pass
        
        time.sleep(2)

    process.terminate()
    return results

if __name__ == "__main__":
    binary = "/Users/dev/Documents/GitHub/atlastrinity/vendor/mcp-server-macos-use/.build/release/mcp-server-macos-use"
    
    # Task: Open Safari, Focus Address Bar, Type URL, Press Enter
    commands = [
        ("macos-use_open_application_and_traverse", {"identifier": "Safari"}),
        ("macos-use_press_key_and_traverse", {"pid": 0, "keyName": "l", "modifierFlags": ["Command"]}),
        ("macos-use_type_and_traverse", {"pid": 0, "text": "https://www.google.com"}),
        ("macos-use_press_key_and_traverse", {"pid": 0, "keyName": "Return"}),
    ]
    
    results = run_mcp_command(binary, commands)
    for i, res in enumerate(results):
        print(f"Step {i} Result: {res[:200]}...")
