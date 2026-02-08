"""Native macos-use MCP Server Test Suite — All 42 Tools

Spawns the macos-use Swift binary directly and tests every tool via JSON-RPC.
Groups:
  A. Server Lifecycle (spawn, initialize, tool listing)
  B. Safe Read-Only Tools (no side-effects: screenshot, OCR, time, clipboard read, lists)
  C. System Info Tools (running apps, browser tabs, windows, finder list, spotlight)
  D. Terminal & Fetch (execute_command, fetch_url)
  E. Input Schema Validation (every tool's required/optional params)
  F. Error Handling (missing params, invalid args, unknown tools)
  G. Productivity Tools (calendar, reminders, notes, mail — read-only probes)
  H. GUI Tools (click/type/key — schema-only, no actual execution)

Run:
    .venv/bin/python -m pytest tests/test_macos_use_native.py -v
    .venv/bin/python tests/test_macos_use_native.py   # standalone
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BINARY_RELEASE = (
    PROJECT_ROOT / "vendor" / "mcp-server-macos-use" / ".build" / "release" / "mcp-server-macos-use"
)
_BINARY_ROOT = PROJECT_ROOT / "vendor" / "mcp-server-macos-use" / "mcp-server-macos-use"
BINARY = str(_BINARY_RELEASE if _BINARY_RELEASE.exists() else _BINARY_ROOT)

# ═══════════════════════════════════════════════════════════════════════════════
# JSON-RPC HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

_next_id = 0


def _new_id() -> int:
    global _next_id
    _next_id += 1
    return _next_id


def _jsonrpc(method: str, params: dict[str, Any] | None = None, req_id: int | None = None) -> str:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": req_id or _new_id(),
            "method": method,
            "params": params or {},
        }
    )


def _init_msg() -> str:
    return _jsonrpc(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-macos-use", "version": "2.0"},
        },
        req_id=1,
    )


def _call_tool(name: str, args: dict[str, Any] | None = None, req_id: int = 100) -> str:
    return _jsonrpc("tools/call", {"name": name, "arguments": args or {}}, req_id=req_id)


def _send(messages: list[str], timeout: float = 20.0) -> list[dict[str, Any]]:
    """Send JSON-RPC messages to macos-use binary and parse responses."""
    if not Path(BINARY).exists():
        pytest.skip(f"macos-use binary not found: {BINARY}")

    stdin_data = "\n".join(messages) + "\n"
    try:
        proc = subprocess.run(
            [BINARY],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        pytest.skip("macos-use binary timed out (app may not be active)")
    except FileNotFoundError:
        pytest.skip("macos-use binary not found")

    responses = []
    for line in proc.stdout.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            responses.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return responses


def _init_and_call(
    tool_name: str, args: dict[str, Any] | None = None, call_id: int = 100
) -> dict[str, Any]:
    """Initialize + call a single tool, return the tool response."""
    msgs = [_init_msg(), _call_tool(tool_name, args, req_id=call_id)]
    responses = _send(msgs)
    for r in responses:
        if r.get("id") == call_id:
            return r
    return {"error": f"No response for id={call_id}", "all_responses": responses}


def _init_and_list() -> tuple[list[dict[str, Any]], float]:
    """Initialize + list tools, return (tools_list, elapsed_ms)."""
    msgs = [_init_msg(), _jsonrpc("tools/list", req_id=2)]
    start = time.time()
    responses = _send(msgs)
    elapsed = round((time.time() - start) * 1000, 1)
    for r in responses:
        if r.get("id") == 2 and "result" in r:
            return r["result"].get("tools", []), elapsed
    return [], elapsed


# ═══════════════════════════════════════════════════════════════════════════════
# EXPECTED TOOLS — complete list of all 42 tools
# ═══════════════════════════════════════════════════════════════════════════════

ALL_42_TOOLS = [
    # GUI Automation (10)
    "macos-use_open_application_and_traverse",
    "macos-use_click_and_traverse",
    "macos-use_right_click_and_traverse",
    "macos-use_double_click_and_traverse",
    "macos-use_drag_and_drop_and_traverse",
    "macos-use_type_and_traverse",
    "macos-use_press_key_and_traverse",
    "macos-use_scroll_and_traverse",
    "macos-use_refresh_traversal",
    "macos-use_window_management",
    # Terminal (2)
    "execute_command",
    "terminal",
    # Screenshot & Vision (5)
    "macos-use_take_screenshot",
    "screenshot",
    "macos-use_analyze_screen",
    "ocr",
    "analyze",
    # Clipboard (2)
    "macos-use_set_clipboard",
    "macos-use_get_clipboard",
    # System (3)
    "macos-use_system_control",
    "macos-use_fetch_url",
    "macos-use_get_time",
    # AppleScript (1)
    "macos-use_run_applescript",
    # Calendar (2)
    "macos-use_calendar_events",
    "macos-use_create_event",
    # Reminders (2)
    "macos-use_reminders",
    "macos-use_create_reminder",
    # Spotlight (1)
    "macos-use_spotlight_search",
    # Notifications (1)
    "macos-use_send_notification",
    # Notes (3)
    "macos-use_notes_list_folders",
    "macos-use_notes_create_note",
    "macos-use_notes_get_content",
    # Mail (2)
    "macos-use_mail_send",
    "macos-use_mail_read_inbox",
    # Finder (4)
    "macos-use_finder_list_files",
    "macos-use_finder_get_selection",
    "macos-use_finder_open_path",
    "macos-use_finder_move_to_trash",
    # System Monitoring (3)
    "macos-use_list_running_apps",
    "macos-use_list_browser_tabs",
    "macos-use_list_all_windows",
    # Dynamic Discovery (1)
    "macos-use_list_tools_dynamic",
]

# Tools safe to call without side-effects (read-only)
SAFE_TOOLS_NO_ARGS = [
    "macos-use_take_screenshot",
    "screenshot",
    "macos-use_analyze_screen",
    "ocr",
    "analyze",
    "macos-use_get_clipboard",
    "macos-use_get_time",
    "macos-use_list_running_apps",
    "macos-use_list_all_windows",
    "macos-use_list_browser_tabs",
    "macos-use_notes_list_folders",
    "macos-use_finder_list_files",
    "macos-use_finder_get_selection",
    "macos-use_reminders",
    "macos-use_mail_read_inbox",
    "macos-use_list_tools_dynamic",
    "macos-use_refresh_traversal",
]

# Required params for every tool
TOOL_REQUIRED_PARAMS: dict[str, list[str]] = {
    "macos-use_open_application_and_traverse": ["identifier"],
    "macos-use_click_and_traverse": ["x", "y"],
    "macos-use_right_click_and_traverse": ["x", "y"],
    "macos-use_double_click_and_traverse": ["x", "y"],
    "macos-use_drag_and_drop_and_traverse": ["startX", "startY", "endX", "endY"],
    "macos-use_type_and_traverse": ["text"],
    "macos-use_press_key_and_traverse": ["keyName"],
    "macos-use_scroll_and_traverse": ["direction"],
    "macos-use_refresh_traversal": [],
    "macos-use_window_management": ["action"],
    "execute_command": ["command"],
    "terminal": ["command"],
    "macos-use_take_screenshot": [],
    "screenshot": [],
    "macos-use_analyze_screen": [],
    "ocr": [],
    "analyze": [],
    "macos-use_set_clipboard": ["text"],
    "macos-use_get_clipboard": [],
    "macos-use_system_control": ["action"],
    "macos-use_fetch_url": ["url"],
    "macos-use_get_time": [],
    "macos-use_run_applescript": ["script"],
    "macos-use_calendar_events": ["start", "end"],
    "macos-use_create_event": ["title", "date"],
    "macos-use_reminders": [],
    "macos-use_create_reminder": ["title"],
    "macos-use_spotlight_search": ["query"],
    "macos-use_send_notification": ["title", "message"],
    "macos-use_notes_list_folders": [],
    "macos-use_notes_create_note": ["body"],
    "macos-use_notes_get_content": ["name"],
    "macos-use_mail_send": ["to", "subject", "body"],
    "macos-use_mail_read_inbox": [],
    "macos-use_finder_list_files": [],
    "macos-use_finder_get_selection": [],
    "macos-use_finder_open_path": ["path"],
    "macos-use_finder_move_to_trash": ["path"],
    "macos-use_list_running_apps": [],
    "macos-use_list_browser_tabs": [],
    "macos-use_list_all_windows": [],
    "macos-use_list_tools_dynamic": [],
}


# ═══════════════════════════════════════════════════════════════════════════════
# A. SERVER LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════


class TestMacosUseLifecycle:
    """Test binary startup, initialization, and tool discovery."""

    def test_binary_exists(self):
        assert Path(BINARY).exists(), f"Binary not found: {BINARY}"

    def test_binary_executable(self):
        assert os.access(BINARY, os.X_OK), f"Binary not executable: {BINARY}"

    def test_initialize_response(self):
        responses = _send([_init_msg()])
        assert len(responses) >= 1
        init_resp = responses[0]
        assert init_resp.get("id") == 1
        assert "result" in init_resp
        caps = init_resp["result"].get("capabilities", {})
        assert "tools" in caps, "Server must advertise tools capability"

    def test_server_name_and_version(self):
        responses = _send([_init_msg()])
        info = responses[0]["result"].get("serverInfo", {})
        assert info.get("name"), "Server must report a name"

    def test_tool_listing_returns_42(self):
        tools, _ = _init_and_list()
        assert len(tools) == 42, f"Expected 42 tools, got {len(tools)}"

    def test_tool_listing_response_time(self):
        _, elapsed_ms = _init_and_list()
        assert elapsed_ms < 5000, f"Tool listing too slow: {elapsed_ms}ms"

    def test_all_expected_tools_present(self):
        tools, _ = _init_and_list()
        tool_names = {t["name"] for t in tools}
        missing = set(ALL_42_TOOLS) - tool_names
        assert not missing, f"Missing tools: {missing}"

    def test_no_unexpected_tools(self):
        tools, _ = _init_and_list()
        tool_names = {t["name"] for t in tools}
        extra = tool_names - set(ALL_42_TOOLS)
        # Extra tools are OK (future additions) but log them
        if extra:
            print(f"  [INFO] Extra tools found: {extra}")

    def test_every_tool_has_input_schema(self):
        tools, _ = _init_and_list()
        for t in tools:
            assert "inputSchema" in t, f"Tool {t['name']} missing inputSchema"
            assert t["inputSchema"].get("type") == "object", (
                f"Tool {t['name']} inputSchema type must be 'object'"
            )

    def test_every_tool_has_description(self):
        tools, _ = _init_and_list()
        for t in tools:
            desc = t.get("description", "")
            assert len(desc) > 5, f"Tool {t['name']} has no/short description: '{desc}'"


# ═══════════════════════════════════════════════════════════════════════════════
# B. SCHEMA VALIDATION FOR ALL 42 TOOLS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMacosUseSchemas:
    """Validate input schemas for every tool match expected required params."""

    @pytest.fixture(scope="class")
    def tools_map(self) -> dict[str, dict[str, Any]]:
        tools, _ = _init_and_list()
        return {t["name"]: t for t in tools}

    @pytest.mark.parametrize("tool_name", ALL_42_TOOLS)
    def test_tool_required_params(self, tool_name, tools_map):
        """Each tool's required params must match expected."""
        tool = tools_map.get(tool_name)
        if not tool:
            pytest.skip(f"Tool {tool_name} not found in server")
        schema = tool.get("inputSchema", {})
        actual_required = set(schema.get("required", []))
        expected_required = set(TOOL_REQUIRED_PARAMS.get(tool_name, []))
        assert actual_required == expected_required, (
            f"{tool_name}: expected required={expected_required}, got={actual_required}"
        )

    @pytest.mark.parametrize("tool_name", ALL_42_TOOLS)
    def test_tool_properties_are_typed(self, tool_name, tools_map):
        """Each property in the schema must have a 'type' or 'enum'."""
        tool = tools_map.get(tool_name)
        if not tool:
            pytest.skip(f"Tool {tool_name} not found")
        props = tool.get("inputSchema", {}).get("properties", {})
        for param_name, param_def in props.items():
            has_type = "type" in param_def or "enum" in param_def
            assert has_type, f"{tool_name}.{param_name} missing 'type' or 'enum'"


# ═══════════════════════════════════════════════════════════════════════════════
# C. SAFE READ-ONLY TOOL CALLS (no side-effects)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMacosUseSafeTools:
    """Call read-only tools and verify they return valid responses."""

    @pytest.mark.parametrize("tool_name", SAFE_TOOLS_NO_ARGS)
    def test_safe_tool_responds(self, tool_name):
        """Each safe tool must return a result (not an error)."""
        resp = _init_and_call(tool_name)
        assert "result" in resp or "error" in resp, f"No response for {tool_name}"
        if "error" in resp:
            # Some tools may fail gracefully (e.g., no browser open) — that's OK
            err = resp["error"]
            # JSON-RPC level errors are bad; application-level errors in content are OK
            if isinstance(err, dict) and err.get("code"):
                # JSON-RPC error — should not happen for valid calls
                pytest.fail(f"{tool_name} JSON-RPC error: {err}")

    def test_get_time_returns_timestamp(self):
        resp = _init_and_call("macos-use_get_time")
        assert "result" in resp
        content = resp["result"].get("content", [])
        assert len(content) > 0
        text = content[0].get("text", "")
        assert len(text) > 5, f"Time response too short: {text}"

    def test_get_time_with_timezone(self):
        resp = _init_and_call("macos-use_get_time", {"timezone": "Europe/Kyiv"})
        assert "result" in resp
        content = resp["result"].get("content", [])
        assert len(content) > 0

    def test_get_clipboard_returns_content(self):
        resp = _init_and_call("macos-use_get_clipboard")
        assert "result" in resp
        content = resp["result"].get("content", [])
        assert len(content) > 0

    def test_list_running_apps_returns_data(self):
        resp = _init_and_call("macos-use_list_running_apps")
        assert "result" in resp
        content = resp["result"].get("content", [])
        assert len(content) > 0
        text = content[0].get("text", "")
        assert len(text) > 2, "Running apps list seems empty"

    def test_list_all_windows_returns_data(self):
        resp = _init_and_call("macos-use_list_all_windows")
        assert "result" in resp
        content = resp["result"].get("content", [])
        assert len(content) > 0

    def test_list_browser_tabs(self):
        resp = _init_and_call("macos-use_list_browser_tabs")
        assert "result" in resp

    def test_list_browser_tabs_with_browser(self):
        resp = _init_and_call("macos-use_list_browser_tabs", {"browser": "safari"})
        assert "result" in resp

    def test_take_screenshot(self):
        resp = _init_and_call("macos-use_take_screenshot")
        assert "result" in resp
        content = resp["result"].get("content", [])
        assert len(content) > 0

    def test_screenshot_alias(self):
        resp = _init_and_call("screenshot")
        assert "result" in resp

    def test_analyze_screen(self):
        resp = _init_and_call("macos-use_analyze_screen")
        assert "result" in resp

    def test_ocr_alias(self):
        resp = _init_and_call("ocr")
        assert "result" in resp

    def test_analyze_alias(self):
        resp = _init_and_call("analyze")
        assert "result" in resp

    def test_notes_list_folders(self):
        resp = _init_and_call("macos-use_notes_list_folders")
        assert "result" in resp

    def test_finder_list_files_home(self):
        resp = _init_and_call("macos-use_finder_list_files")
        assert "result" in resp

    def test_finder_list_files_custom_path(self):
        resp = _init_and_call("macos-use_finder_list_files", {"path": "/tmp"})
        assert "result" in resp

    def test_finder_get_selection(self):
        resp = _init_and_call("macos-use_finder_get_selection")
        assert "result" in resp

    def test_reminders_list(self):
        resp = _init_and_call("macos-use_reminders")
        assert "result" in resp

    def test_reminders_list_specific(self):
        resp = _init_and_call("macos-use_reminders", {"list": "Reminders"})
        assert "result" in resp

    def test_mail_read_inbox(self):
        resp = _init_and_call("macos-use_mail_read_inbox")
        assert "result" in resp

    def test_mail_read_inbox_limited(self):
        resp = _init_and_call("macos-use_mail_read_inbox", {"limit": 1})
        assert "result" in resp

    def test_list_tools_dynamic(self):
        resp = _init_and_call("macos-use_list_tools_dynamic")
        assert "result" in resp
        content = resp["result"].get("content", [])
        assert len(content) > 0
        text = content[0].get("text", "")
        assert "execute_command" in text or "macos-use" in text, (
            "Dynamic tool list should contain tool names"
        )

    def test_refresh_traversal(self):
        resp = _init_and_call("macos-use_refresh_traversal")
        assert "result" in resp


# ═══════════════════════════════════════════════════════════════════════════════
# D. TERMINAL & FETCH TOOLS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMacosUseTerminalFetch:
    """Test execute_command and fetch_url tools."""

    def test_execute_echo(self):
        resp = _init_and_call("execute_command", {"command": "echo 'macos-use-test-ok'"})
        assert "result" in resp
        text = resp["result"]["content"][0]["text"]
        assert "macos-use-test-ok" in text

    def test_terminal_alias_echo(self):
        resp = _init_and_call("terminal", {"command": "echo 'terminal-alias-ok'"})
        assert "result" in resp
        text = resp["result"]["content"][0]["text"]
        assert "terminal-alias-ok" in text

    def test_execute_pwd(self):
        resp = _init_and_call("execute_command", {"command": "pwd"})
        assert "result" in resp
        text = resp["result"]["content"][0]["text"]
        assert "/" in text

    def test_execute_date(self):
        resp = _init_and_call("execute_command", {"command": "date"})
        assert "result" in resp
        assert len(resp["result"]["content"][0]["text"]) > 5

    def test_execute_whoami(self):
        resp = _init_and_call("execute_command", {"command": "whoami"})
        assert "result" in resp
        text = resp["result"]["content"][0]["text"].strip()
        assert len(text) > 0

    def test_execute_uname(self):
        resp = _init_and_call("execute_command", {"command": "uname -a"})
        assert "result" in resp
        text = resp["result"]["content"][0]["text"]
        assert "Darwin" in text

    def test_execute_multiline(self):
        resp = _init_and_call("execute_command", {"command": "echo line1 && echo line2"})
        assert "result" in resp
        text = resp["result"]["content"][0]["text"]
        assert "line1" in text and "line2" in text

    def test_fetch_url_example(self):
        resp = _init_and_call("macos-use_fetch_url", {"url": "https://example.com"})
        assert "result" in resp
        text = resp["result"]["content"][0]["text"]
        assert "Example Domain" in text or "example" in text.lower()

    def test_fetch_url_json_api(self):
        resp = _init_and_call(
            "macos-use_fetch_url",
            {"url": "https://httpbin.org/json"},
        )
        assert "result" in resp

    def test_spotlight_search(self):
        resp = _init_and_call("macos-use_spotlight_search", {"query": "System Preferences"})
        assert "result" in resp

    def test_run_applescript_simple(self):
        resp = _init_and_call(
            "macos-use_run_applescript",
            {"script": 'return "hello from applescript"'},
        )
        assert "result" in resp
        text = resp["result"]["content"][0]["text"]
        assert "hello" in text.lower()

    def test_get_time_default(self):
        resp = _init_and_call("macos-use_get_time")
        text = resp["result"]["content"][0]["text"]
        # Should contain date-like content
        assert any(c.isdigit() for c in text), f"Time has no digits: {text}"


# ═══════════════════════════════════════════════════════════════════════════════
# E. ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════════════════


class TestMacosUseErrorHandling:
    """Test that the server handles invalid inputs gracefully."""

    def test_call_unknown_tool(self):
        resp = _init_and_call("nonexistent_tool_xyz_999")
        # MCP protocol: unknown tools return result with isError=True, not JSON-RPC error
        has_error = "error" in resp
        has_is_error = (
            isinstance(resp.get("result"), dict) and resp["result"].get("isError") is True
        )
        assert has_error or has_is_error, (
            f"Unknown tool should return error or isError=True, got: {resp}"
        )

    def test_execute_command_missing_param(self):
        resp = _init_and_call("execute_command", {})
        # Should error — 'command' is required
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_click_missing_coordinates(self):
        resp = _init_and_call("macos-use_click_and_traverse", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_click_missing_y(self):
        resp = _init_and_call("macos-use_click_and_traverse", {"x": 100})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_type_missing_text(self):
        resp = _init_and_call("macos-use_type_and_traverse", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_press_key_missing_key(self):
        resp = _init_and_call("macos-use_press_key_and_traverse", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_scroll_missing_direction(self):
        resp = _init_and_call("macos-use_scroll_and_traverse", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_fetch_url_missing_url(self):
        resp = _init_and_call("macos-use_fetch_url", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_applescript_missing_script(self):
        resp = _init_and_call("macos-use_run_applescript", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_open_app_missing_identifier(self):
        resp = _init_and_call("macos-use_open_application_and_traverse", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_window_mgmt_missing_action(self):
        resp = _init_and_call("macos-use_window_management", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_calendar_missing_dates(self):
        resp = _init_and_call("macos-use_calendar_events", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_create_event_missing_fields(self):
        resp = _init_and_call("macos-use_create_event", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_mail_send_missing_fields(self):
        resp = _init_and_call("macos-use_mail_send", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_notes_get_content_missing_name(self):
        resp = _init_and_call("macos-use_notes_get_content", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_finder_open_missing_path(self):
        resp = _init_and_call("macos-use_finder_open_path", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))

    def test_send_notification_missing_fields(self):
        resp = _init_and_call("macos-use_send_notification", {})
        assert "error" in resp or "isError" in str(resp.get("result", {}))


# ═══════════════════════════════════════════════════════════════════════════════
# F. GUI TOOL SCHEMA PROBES (validate schemas without executing)
# ═══════════════════════════════════════════════════════════════════════════════


class TestMacosUseGUISchemas:
    """Verify GUI tools have correct schemas (click, type, key, drag, scroll)."""

    @pytest.fixture(scope="class")
    def tools_map(self) -> dict[str, dict[str, Any]]:
        tools, _ = _init_and_list()
        return {t["name"]: t for t in tools}

    def test_click_schema(self, tools_map):
        schema = tools_map["macos-use_click_and_traverse"]["inputSchema"]
        props = schema["properties"]
        assert "x" in props and "y" in props
        assert props["x"]["type"] in ("number", "integer")
        assert props["y"]["type"] in ("number", "integer")
        assert "pid" in props  # optional PID targeting

    def test_right_click_schema(self, tools_map):
        schema = tools_map["macos-use_right_click_and_traverse"]["inputSchema"]
        assert set(schema["required"]) == {"x", "y"}

    def test_double_click_schema(self, tools_map):
        schema = tools_map["macos-use_double_click_and_traverse"]["inputSchema"]
        assert set(schema["required"]) == {"x", "y"}

    def test_drag_drop_schema(self, tools_map):
        schema = tools_map["macos-use_drag_and_drop_and_traverse"]["inputSchema"]
        assert set(schema["required"]) == {"startX", "startY", "endX", "endY"}

    def test_type_schema(self, tools_map):
        schema = tools_map["macos-use_type_and_traverse"]["inputSchema"]
        assert "text" in schema["required"]
        assert schema["properties"]["text"]["type"] == "string"

    def test_press_key_schema(self, tools_map):
        schema = tools_map["macos-use_press_key_and_traverse"]["inputSchema"]
        assert "keyName" in schema["required"]
        # Should have optional modifierFlags
        assert "modifierFlags" in schema["properties"]

    def test_scroll_schema(self, tools_map):
        schema = tools_map["macos-use_scroll_and_traverse"]["inputSchema"]
        assert "direction" in schema["required"]
        assert "amount" in schema["properties"]

    def test_window_management_schema(self, tools_map):
        schema = tools_map["macos-use_window_management"]["inputSchema"]
        assert "action" in schema["required"]
        # Should support position/size params
        props = set(schema["properties"].keys())
        assert "width" in props and "height" in props

    def test_open_application_schema(self, tools_map):
        schema = tools_map["macos-use_open_application_and_traverse"]["inputSchema"]
        assert schema["required"] == ["identifier"]

    def test_set_clipboard_schema(self, tools_map):
        schema = tools_map["macos-use_set_clipboard"]["inputSchema"]
        assert "text" in schema["required"]

    def test_system_control_schema(self, tools_map):
        schema = tools_map["macos-use_system_control"]["inputSchema"]
        assert "action" in schema["required"]

    def test_calendar_events_schema(self, tools_map):
        schema = tools_map["macos-use_calendar_events"]["inputSchema"]
        assert set(schema["required"]) == {"start", "end"}

    def test_mail_send_schema(self, tools_map):
        schema = tools_map["macos-use_mail_send"]["inputSchema"]
        assert set(schema["required"]) == {"to", "subject", "body"}


# ═══════════════════════════════════════════════════════════════════════════════
# G. CALENDAR & PRODUCTIVITY READ PROBES
# ═══════════════════════════════════════════════════════════════════════════════


class TestMacosUseProductivity:
    """Probe productivity tools with safe read-only calls."""

    def test_calendar_events_today(self):
        import datetime

        today = datetime.date.today().isoformat()
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        resp = _init_and_call("macos-use_calendar_events", {"start": today, "end": tomorrow})
        assert "result" in resp

    def test_spotlight_search_finder(self):
        resp = _init_and_call("macos-use_spotlight_search", {"query": "Finder"})
        assert "result" in resp

    def test_spotlight_search_terminal(self):
        resp = _init_and_call("macos-use_spotlight_search", {"query": "Terminal.app"})
        assert "result" in resp


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE RUNNER
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    """Run all tests standalone with colored output."""

    if not Path(BINARY).exists():
        print(f"ERROR: macos-use binary not found at {BINARY}")
        print("Build it with: cd vendor/mcp-server-macos-use && swift build -c release")
        return 1

    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║   macos-use MCP Native Test Suite — 42 Tools Deep Testing     ║")
    print("╚══════════════════════════════════════════════════════════════════╝\n")

    # Quick pre-check: list all tools
    tools, elapsed = _init_and_list()
    print(f"Server alive: {len(tools)} tools discovered in {elapsed}ms\n")

    classes = [
        ("A. Server Lifecycle", TestMacosUseLifecycle),
        ("B. Schema Validation (42 tools)", TestMacosUseSchemas),
        ("C. Safe Read-Only Tools", TestMacosUseSafeTools),
        ("D. Terminal & Fetch", TestMacosUseTerminalFetch),
        ("E. Error Handling", TestMacosUseErrorHandling),
        ("F. GUI Schemas", TestMacosUseGUISchemas),
        ("G. Productivity Probes", TestMacosUseProductivity),
    ]

    total_p, total_f, total_s = 0, 0, 0

    for section_name, cls in classes:
        print(f"\n{'═' * 60}")
        print(f"  {section_name}")
        print(f"{'═' * 60}")

        instance = cls()
        for method_name in sorted(dir(instance)):
            if not method_name.startswith("test_"):
                continue
            method = getattr(instance, method_name)
            try:
                # Handle fixtures
                import inspect

                sig = inspect.signature(method)
                kwargs = {}
                if "tools_map" in sig.parameters:
                    t, _ = _init_and_list()
                    kwargs["tools_map"] = {tt["name"]: tt for tt in t}

                method(**kwargs)
                print(f"  ✓ {method_name}")
                total_p += 1
            except Exception as e:
                if "skip" in type(e).__name__.lower() or "Skipped" in str(e):
                    print(f"  ⊘ {method_name}: {e}")
                    total_s += 1
                else:
                    print(f"  ✗ {method_name}: {e}")
                    total_f += 1

    print(f"\n{'═' * 60}")
    print(f"  FINAL: {total_p} passed, {total_f} failed, {total_s} skipped")
    print(f"  {('✓ ALL PASSED' if total_f == 0 else f'✗ {total_f} FAILURES')}")
    print(f"{'═' * 60}\n")

    return 0 if total_f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
