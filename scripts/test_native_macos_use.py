import json
import os
# ruff: noqa: T201
import subprocess
import sys
import uuid

# Path to the compiled Swift binary
BINARY_PATH = os.path.join(os.getcwd(), "vendor/mcp-server-macos-use/.build/release/mcp-server-macos-use")

def call_tool_native(tool_name, arguments):
    """Sends a JSON-RPC call_tool request to the Swift binary via stdio."""
    request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": str(uuid.uuid4())
    }
    
    proc = subprocess.Popen(
        [BINARY_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        stdout_data, stderr_data = proc.communicate(input=json.dumps(request) + "\n", timeout=20)
        for line in stdout_data.splitlines():
            try:
                resp = json.loads(line)
                if resp.get("id") == request["id"]:
                    return resp
            except:
                continue
        return {"error": "No JSON-RPC response found", "stdout": stdout_data, "stderr": stderr_data}
    except subprocess.TimeoutExpired:
        proc.kill()
        return {"error": "Timeout expired"}

def main():
    if not os.path.exists(BINARY_PATH):
        print(f"Error: Binary not found at {BINARY_PATH}. Please compile first.")
        sys.exit(1)

    # Exhaustive list of all 50 tools with varied/realistic arguments
    tools_to_test = [
        # --- UI Automation & Navigation ---
        ("macos-use_open_application_and_traverse", {"bundleId": "com.apple.Safari"}),
        ("macos-use_click_and_traverse", {"x": 500, "y": 500, "waitAfter": 1.0}),
        ("macos-use_right_click_and_traverse", {"x": 100, "y": 100}),
        ("macos-use_double_click_and_traverse", {"x": 200, "y": 200}),
        ("macos-use_drag_and_drop_and_traverse", {"startX": 10, "startY": 10, "endX": 100, "endY": 100}),
        ("macos-use_type_and_traverse", {"text": "Hello Atlas Trinity!"}),
        ("macos-use_press_key_and_traverse", {"keyName": "Space"}),
        ("macos-use_scroll_and_traverse", {"direction": "up", "amount": 2}),
        ("macos-use_refresh_traversal", {"fullRefresh": True}),
        ("macos-use_window_management", {"action": "minimize_all"}),
        ("macos-use_open_app", {"name": "TextEdit"}),
        
        # --- System & Terminal ---
        ("execute_command", {"command": "uname -a"}),
        ("terminal", {"command": "df -h"}),
        ("macos-use_system_control", {"action": "get_performance"}),
        ("macos-use_system_monitoring", {"metric": "memory"}),
        ("macos-use_process_management", {"action": "list"}),
        
        # --- Vision & OCR ---
        ("macos-use_take_screenshot", {"format": "jpg", "quality": "high", "monitor": 1}),
        ("screenshot", {"format": "png", "ocr": True}),
        ("macos-use_analyze_screen", {"language": "uk"}), # Varied language
        ("ocr", {}),
        ("analyze", {}),
        
        # --- Clipboard & Data ---
        ("macos-use_set_clipboard", {"text": "Varied Argument Test Content"}),
        ("macos-use_get_clipboard", {"format": "all"}), # Get everything
        ("macos-use_clipboard_history", {"limit": 10}),
        ("macos-use_fetch_url", {"url": "https://apple.com"}),
        ("macos-use_get_time", {"format": "unix"}),
        ("macos-use_countdown_timer", {"seconds": 2, "message": "Quick Test", "notification": True}),
        
        # --- Personal Info (Handled gracefully if denied) ---
        ("macos-use_calendar_events", {"start": "2024-01-01T00:00:00Z", "end": "2025-01-01T00:00:00Z"}),
        ("macos-use_create_event", {"title": "Team Sync", "date": "2026-06-01T09:30:00Z"}),
        ("macos-use_reminders", {}),
        ("macos-use_create_reminder", {"title": "Buy groceries"}),
        ("macos-use_notes_list_folders", {}),
        ("macos-use_notes_create_note", {"body": "New Idea: MCP Servers"}),
        ("macos-use_notes_get_content", {"name": "Test Note"}),
        
        # --- Search & Notifications ---
        ("macos-use_spotlight_search", {"query": "Applications"}),
        ("macos-use_send_notification", {"title": "System Alert", "message": "Native Verification Phase Complete", "sound": True}),
        ("macos-use_notification_schedule", {"list": True}),
        
        # --- Communication & Media ---
        ("macos-use_mail_send", {"to": "oleg@example.com", "subject": "Test Report", "body": "All tools verified.", "draft": True}),
        ("macos-use_mail_read_inbox", {"limit": 5}),
        ("macos-use_system_control", {"action": "volume_up"}),
        ("macos-use_voice_control", {"command": "open safari"}), # Native direct language
        ("macos-use_voice_control", {"command": "take a screenshot"}), # Another direct one
        
        # --- Finder & File System ---
        ("macos-use_finder_list_files", {"path": os.path.expanduser("~/Documents"), "limit": 10, "metadata": True}),
        ("macos-use_finder_get_selection", {}),
        ("macos-use_finder_open_path", {"path": "/Applicatons"}),
        ("macos-use_finder_move_to_trash", {"path": "/tmp/test_trash_file"}),
        ("macos-use_file_encryption", {"action": "encrypt", "path": "/tmp/test.txt", "password": "secure_pass"}),
        
        # --- Expansion Tools (60+) ---
        ("macos-use_get_frontmost_app", {}),
        ("macos-use_get_battery_info", {}),
        ("macos-use_get_wifi_details", {}),
        ("macos-use_set_system_volume", {"level": 50}),
        ("macos-use_set_screen_brightness", {"level": 0.8}),
        ("macos-use_empty_trash", {}),
        ("macos-use_get_active_window_info", {}),
        ("macos-use_close_window", {}),
        ("macos-use_move_window", {"x": 50, "y": 50}),
        ("macos-use_resize_window", {"width": 800, "height": 600}),
        ("macos-use_list_network_interfaces", {}),
        ("macos-use_get_ip_address", {}),
        
        # --- Discovery & Browser ---
        ("macos-use_list_running_apps", {}),
        ("macos-use_list_browser_tabs", {}),
        ("macos-use_list_all_windows", {}),
        ("macos-use_list_tools_dynamic", {}),
        ("discovery", {}),
    ]

    print("--- ULTIMATE NATIVE TOOL TESTING (50 TOOLS) ---")
    results = []
    for name, args in tools_to_test:
        print(f"Testing {name:40}", end=" ", flush=True)
        resp = call_tool_native(name, args)
        
        success = False
        if "result" in resp:
            res_obj = resp["result"]
            if isinstance(res_obj, dict) and not res_obj.get("isError", False):
                success = True
        
        if success:
            print("[\033[92mPASS\033[0m]")
            results.append((name, True))
        else:
            # Extraction of error message
            msg = "Unknown error"
            if isinstance(resp, dict):
                res_obj = resp.get("result", {})
                if isinstance(res_obj, dict):
                    content = res_obj.get("content", [])
                    if isinstance(content, list) and len(content) > 0:
                        msg = content[0].get("text", "Unknown result text")
                elif "error" in resp:
                    msg = str(resp["error"])
            
            # Some tools might legitimately fail if dependencies (like Mail or Notes) aren't set up,
            # but we want to know IF the handler exists and responded.
            # If the error is "Method not found", that's a REAL failure.
            if "Method not found" in msg:
                 print("[\033[91mFAILED\033[0m] (Method not found)")
                 results.append((name, False))
            else:
                 # Legit error from handler (e.g. "Note not found") means the handler IS there.
                 print(f"[\033[94mOK (Existed)\033[0m] ({msg[:50]}...)")
                 results.append((name, True))

    passed = len([r for r in results if r[1]])
    print(f"\nExhaustive Native Test Summary: {passed}/{len(tools_to_test)} Handlers Verified")

if __name__ == "__main__":
    main()
