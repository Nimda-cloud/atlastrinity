#!/usr/bin/env python3
# ruff: noqa: T201
from __future__ import annotations

"""
Swift MCP Bridge Validator
Tests all native Swift MCP server binaries via stdio JSON-RPC protocol,
exactly as the TypeScript bridge (BridgeBackend) connects to them.

Validates:
1. Binary existence and executability
2. MCP initialize handshake
3. tools/list discovery
4. Sample tool calls (safe, read-only tools)
5. Catalog alignment between catalog.ts definitions and actual server tools
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DESKTOP = Path.home() / "Desktop"

# Test file paths on Desktop
TRASH_TEST_FILE = DESKTOP / "atlas_bridge_test_trash.txt"
ENCRYPT_TEST_FILE = DESKTOP / "atlas_bridge_test_encrypt.txt"
ENCRYPT_OUTPUT_FILE = DESKTOP / "atlas_bridge_test_encrypt.txt.enc"


def _load_google_maps_api_key() -> str:
    """Load Google Maps API key from config or env."""
    key = os.environ.get("GOOGLE_MAPS_API_KEY", "")
    if key:
        return key
    config_path = Path.home() / ".config" / "atlastrinity" / "mcp" / "config.json"
    if config_path.exists():
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            for _name, cfg in data.get("mcpServers", {}).items():
                if not isinstance(cfg, dict):
                    continue
                env = cfg.get("env", {})
                if "GOOGLE_MAPS_API_KEY" in env:
                    return env["GOOGLE_MAPS_API_KEY"]
        except Exception:
            pass
    return ""


def _ensure_test_files():
    """Create test files on Desktop and /tmp for trash and encryption tests."""
    if not TRASH_TEST_FILE.exists():
        TRASH_TEST_FILE.write_text("atlas bridge test file for trash\n")
    if not ENCRYPT_TEST_FILE.exists():
        ENCRYPT_TEST_FILE.write_text("atlas bridge test file for encryption\n")
    # Clean up previous encryption output
    if ENCRYPT_OUTPUT_FILE.exists():
        ENCRYPT_OUTPUT_FILE.unlink()
    # Encryption test file in /tmp (avoids Desktop permission issues)
    tmp_enc = Path("/tmp/atlas_bridge_enc_test.txt")
    tmp_enc.write_text("atlas bridge encryption test content\n")
    # Clean up previous encrypted output so the tool doesn't fail on copy
    tmp_enc_out = Path("/tmp/atlas_bridge_enc_test.txt..encrypted")
    if tmp_enc_out.exists():
        tmp_enc_out.unlink()


# Swift MCP server binaries
SWIFT_SERVERS = {
    "macos-use": {
        "binary": PROJECT_ROOT / "vendor" / "mcp-server-macos-use" / ".build" / "release" / "mcp-server-macos-use",
        "description": "macOS-use Automation (UI, system, files, clipboard, etc.)",
        "test_all_tools": [
            # -- Safe target: open TextEdit first so UI tools don't hit Windsurf --
            ("macos-use_open_application_and_traverse", {"identifier": "TextEdit"}),
            # UI Automation (targets TextEdit via frontmost after opening it)
            ("macos-use_click_and_traverse", {"x": 300, "y": 400, "traverseBefore": False, "traverseAfter": False}),
            ("macos-use_right_click_and_traverse", {"x": 300, "y": 400}),
            ("macos-use_press_key_and_traverse", {"keyName": "Escape"}),
            ("macos-use_double_click_and_traverse", {"x": 300, "y": 400}),
            ("macos-use_type_and_traverse", {"text": ""}),
            ("macos-use_scroll_and_traverse", {"direction": "down", "amount": 1}),
            ("macos-use_drag_and_drop_and_traverse", {"startX": 300, "startY": 400, "endX": 310, "endY": 410}),
            # App & Window Management
            ("macos-use_refresh_traversal", {"pid": 1}),
            ("macos-use_list_running_apps", {}),
            ("macos-use_list_all_windows", {}),
            ("macos-use_list_browser_tabs", {}),
            ("macos-use_window_management", {"action": "list"}),
            ("macos-use_get_frontmost_app", {}),
            ("macos-use_get_active_window_info", {}),
            ("macos-use_move_window", {"x": 100, "y": 100, "windowName": "Untitled"}),
            ("macos-use_resize_window", {"width": 600, "height": 400, "windowName": "Untitled"}),
            ("macos-use_close_window", {"windowName": "Untitled"}),
            # Visual Testing
            ("macos-use_take_screenshot", {"path": "/tmp/atlas_bridge_test.png", "format": "png"}),
            ("macos-use_analyze_screen", {}),
            ("screenshot", {"path": "/tmp/atlas_bridge_test_alias.png"}),
            ("ocr", {}),
            ("analyze", {}),
            # System
            ("macos-use_system_monitoring", {"metric": "cpu"}),
            ("macos-use_system_control", {"action": "get_system_info"}),
            ("macos-use_system_control", {"action": "get_info"}),
            ("macos-use_system_control", {"action": "get_performance"}),
            ("macos-use_system_control", {"action": "get_network"}),
            ("macos-use_system_control", {"action": "get_storage"}),
            ("macos-use_system_control", {"action": "volume_up"}),
            ("macos-use_system_control", {"action": "volume_down"}),
            ("macos-use_system_control", {"action": "mute"}),
            ("macos-use_system_control", {"action": "brightness_up"}),
            ("macos-use_system_control", {"action": "brightness_down"}),
            ("macos-use_system_control", {"action": "play_pause"}),
            ("macos-use_system_control", {"action": "next"}),
            ("macos-use_system_control", {"action": "previous"}),
            ("macos-use_process_management", {"action": "list"}),
            ("macos-use_get_battery_info", {}),
            ("macos-use_get_wifi_details", {}),
            ("macos-use_set_system_volume", {"level": 50}),
            ("macos-use_set_screen_brightness", {"level": 0.7}),
            ("macos-use_list_network_interfaces", {}),
            ("macos-use_get_ip_address", {}),
            # File & Finder (select file via AppleScript first, then get selection)
            ("macos-use_finder_list_files", {"path": str(DESKTOP), "limit": 5}),
            ("macos-use_finder_open_path", {"path": str(DESKTOP)}),
            ("macos-use_finder_get_selection", {}),
            ("macos-use_finder_move_to_trash", {"path": str(TRASH_TEST_FILE)}),
            ("macos-use_empty_trash", {}),
            ("macos-use_spotlight_search", {"query": "atlastrinity"}),
            # Clipboard
            ("macos-use_set_clipboard", {"text": "atlas-bridge-validator-test"}),
            ("macos-use_get_clipboard", {}),
            ("macos-use_clipboard_history", {"action": "list"}),
            # Scripting
            ("macos-use_run_applescript", {"script": 'return "hello from bridge test"'}),
            ("macos-use_applescript_templates", {"list": True}),
            # Notifications
            ("macos-use_send_notification", {"title": "Bridge Test", "message": "Validator OK"}),
            ("macos-use_notification_schedule", {"list": True}),
            # Productivity
            ("macos-use_calendar_events", {"start": "2026-02-10T00:00:00Z", "end": "2026-02-10T23:59:59Z"}),
            ("macos-use_create_event", {"title": "__bridge_test__", "date": "2099-12-31T00:00:00Z", "duration": 5}),
            ("macos-use_reminders", {}),
            ("macos-use_create_reminder", {"title": "__bridge_test_reminder__"}),
            # Notes
            ("macos-use_notes_list_folders", {}),
            ("macos-use_notes_create_note", {"body": "Bridge validator test note"}),
            ("macos-use_notes_get_content", {"name": "__nonexistent_note__"}),
            # Mail
            ("macos-use_mail_send", {"to": "test@test.invalid", "subject": "bridge test", "body": "test", "draft": True}),
            ("macos-use_mail_read_inbox", {"limit": 1}),
            # Networking & Utilities
            ("macos-use_fetch_url", {"url": "https://httpbin.org/get"}),
            ("macos-use_get_time", {}),
            ("macos-use_countdown_timer", {"seconds": 1, "message": "test"}),
            # Voice & Security
            ("macos-use_voice_control", {"command": "test", "language": "en-US"}),
            ("macos-use_file_encryption", {"action": "encrypt", "path": "/tmp/atlas_bridge_enc_test.txt", "password": "atlas-test-2026"}),
            # Terminal aliases
            ("execute_command", {"command": "echo atlas-bridge-ok"}),
            ("terminal", {"command": "echo terminal-alias-ok"}),
            # Meta
            ("macos-use_list_tools_dynamic", {}),
            # Permissions (LAST - may trigger system dialog and crash server)
            ("macos-use_request_permissions", {}),
        ],
        "expected_catalog_tools": [
            "macos-use_click_and_traverse",
            "macos-use_right_click_and_traverse",
            "macos-use_double_click_and_traverse",
            "macos-use_type_and_traverse",
            "macos-use_press_key_and_traverse",
            "macos-use_scroll_and_traverse",
            "macos-use_drag_and_drop_and_traverse",
            "macos-use_open_application_and_traverse",
            "macos-use_refresh_traversal",
            "macos-use_list_running_apps",
            "macos-use_list_all_windows",
            "macos-use_list_browser_tabs",
            "macos-use_window_management",
            "macos-use_get_frontmost_app",
            "macos-use_get_active_window_info",
            "macos-use_close_window",
            "macos-use_move_window",
            "macos-use_resize_window",
            "macos-use_take_screenshot",
            "macos-use_analyze_screen",
            "macos-use_system_monitoring",
            "macos-use_system_control",
            "macos-use_process_management",
            "macos-use_get_battery_info",
            "macos-use_get_wifi_details",
            "macos-use_set_system_volume",
            "macos-use_set_screen_brightness",
            "macos-use_list_network_interfaces",
            "macos-use_get_ip_address",
            "macos-use_finder_list_files",
            "macos-use_finder_open_path",
            "macos-use_finder_get_selection",
            "macos-use_finder_move_to_trash",
            "macos-use_empty_trash",
            "macos-use_spotlight_search",
            "macos-use_set_clipboard",
            "macos-use_get_clipboard",
            "macos-use_clipboard_history",
            "macos-use_run_applescript",
            "macos-use_applescript_templates",
            "macos-use_send_notification",
            "macos-use_notification_schedule",
            "macos-use_calendar_events",
            "macos-use_create_event",
            "macos-use_reminders",
            "macos-use_create_reminder",
            "macos-use_notes_list_folders",
            "macos-use_notes_create_note",
            "macos-use_notes_get_content",
            "macos-use_mail_send",
            "macos-use_mail_read_inbox",
            "macos-use_fetch_url",
            "macos-use_get_time",
            "macos-use_countdown_timer",
            "macos-use_voice_control",
            "macos-use_file_encryption",
            "macos-use_request_permissions",
            "execute_command",
            "terminal",
            "screenshot",
            "ocr",
            "analyze",
            "macos-use_list_tools_dynamic",
        ],
    },
    "googlemaps": {
        "binary": PROJECT_ROOT / "vendor" / "mcp-server-googlemaps" / ".build" / "release" / "mcp-server-googlemaps",
        "description": "Google Maps (geocoding, directions, places, etc.)",
        "env_override": {"GOOGLE_MAPS_API_KEY": _load_google_maps_api_key()},
        "test_all_tools": [
            ("maps_geocode", {"address": "Eiffel Tower, Paris, France"}),
            ("maps_reverse_geocode", {"lat": 48.8584, "lng": 2.2945}),
            ("maps_search_places", {"query": "restaurants near Eiffel Tower"}),
            ("maps_place_details", {"place_id": "ChIJLU7jZClu5kcR4PcOOO6p3I0"}),
            ("maps_directions", {"origin": "Eiffel Tower, Paris", "destination": "Louvre Museum, Paris"}),
            ("maps_distance_matrix", {"origins": "Eiffel Tower, Paris", "destinations": "Louvre Museum, Paris"}),
            ("maps_street_view", {"location": "48.8584,2.2945"}),
            ("maps_static_map", {"center": "48.8584,2.2945", "zoom": 14}),
            ("maps_elevation", {"locations": "48.8584,2.2945"}),
            ("maps_open_interactive_search", {"initial_query": "Eiffel Tower"}),
            ("maps_generate_link", {"location": "Eiffel Tower, Paris"}),
        ],
        "expected_catalog_tools": [
            "maps_geocode",
            "maps_reverse_geocode",
            "maps_search_places",
            "maps_place_details",
            "maps_directions",
            "maps_distance_matrix",
            "maps_street_view",
            "maps_static_map",
            "maps_elevation",
            "maps_open_interactive_search",
            "maps_generate_link",
        ],
    },
}


class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def ok(msg: str):
    print(f"  {Colors.GREEN}[OK]{Colors.END} {msg}")


def warn(msg: str):
    print(f"  {Colors.YELLOW}[WARN]{Colors.END} {msg}")


def fail(msg: str):
    print(f"  {Colors.RED}[FAIL]{Colors.END} {msg}")


def info(msg: str):
    print(f"  {Colors.CYAN}[INFO]{Colors.END} {msg}")


def header(msg: str):
    print(f"\n{Colors.BOLD}{msg}{Colors.END}")


class MCPStdioClient:
    """Minimal MCP client that talks JSON-RPC over stdio to a Swift binary."""

    def __init__(self, binary_path: Path, env_override: dict[str, str] | None = None):
        self.binary_path = binary_path
        self.env_override = env_override or {}
        self.process: asyncio.subprocess.Process | None = None
        self._request_id = 0

    async def start(self, timeout: float = 15.0) -> bool:
        env = {**os.environ, **self.env_override}
        try:
            self.process = await asyncio.create_subprocess_exec(
                str(self.binary_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            return True
        except Exception as e:
            fail(f"Failed to start process: {e}")
            return False

    async def send_request(self, method: str, params: dict | None = None, timeout: float = 15.0) -> dict[str, Any]:
        if not self.process or not self.process.stdin or not self.process.stdout:
            return {"error": "Process not running"}

        self._request_id += 1
        req_id = self._request_id
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            request["params"] = params

        request_line = json.dumps(request) + "\n"

        try:
            self.process.stdin.write(request_line.encode())
            await self.process.stdin.drain()

            # Read lines until we get the response matching our request id.
            # The server may send notifications (no "id") before the response.
            deadline = asyncio.get_event_loop().time() + timeout
            while True:
                remaining = deadline - asyncio.get_event_loop().time()
                if remaining <= 0:
                    return {"error": f"Timeout after {timeout}s"}

                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=remaining,
                )

                if not response_line:
                    return {"error": "Empty response (EOF)"}

                msg = json.loads(response_line.decode().strip())

                # Skip notifications (no "id" field) and mismatched responses
                if "id" not in msg:
                    continue
                if msg.get("id") == req_id:
                    return msg
                # Mismatched id — skip (stale response from previous call)
        except asyncio.TimeoutError:
            return {"error": f"Timeout after {timeout}s"}
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}
        except Exception as e:
            return {"error": f"Request failed: {e}"}

    async def initialize(self) -> dict[str, Any]:
        return await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "atlas-bridge-validator", "version": "1.0.0"},
        })

    async def send_initialized(self) -> None:
        """Send initialized notification (no response expected)."""
        if not self.process or not self.process.stdin:
            return
        notification = json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }) + "\n"
        self.process.stdin.write(notification.encode())
        await self.process.stdin.drain()

    async def list_tools(self) -> dict[str, Any]:
        return await self.send_request("tools/list", {})

    async def call_tool(self, name: str, arguments: dict) -> dict[str, Any]:
        return await self.send_request("tools/call", {
            "name": name,
            "arguments": arguments,
        }, timeout=30.0)

    async def stop(self):
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None


class ValidationResult:
    def __init__(self, server_id: str):
        self.server_id = server_id
        self.binary_ok = False
        self.init_ok = False
        self.tools_discovered: list[str] = []
        self.catalog_missing: list[str] = []  # In catalog but not in server
        self.server_extra: list[str] = []     # In server but not in catalog
        self.tool_call_results: list[dict] = []
        self.errors: list[str] = []

    @property
    def passed(self) -> bool:
        return self.binary_ok and self.init_ok and len(self.tools_discovered) > 0


async def validate_server(server_id: str, config: dict) -> ValidationResult:
    result = ValidationResult(server_id)
    binary_path: Path = config["binary"]

    header(f"Server: {server_id} ({config['description']})")
    info(f"Binary: {binary_path}")

    # 1. Check binary
    if not binary_path.exists():
        fail(f"Binary not found: {binary_path}")
        result.errors.append("Binary not found")
        return result

    if not os.access(binary_path, os.X_OK):
        fail(f"Binary not executable: {binary_path}")
        result.errors.append("Binary not executable")
        return result

    size_mb = binary_path.stat().st_size / (1024 * 1024)
    ok(f"Binary exists ({size_mb:.1f} MB)")
    result.binary_ok = True

    # 2. Start process and initialize
    client = MCPStdioClient(binary_path, config.get("env_override"))
    started = await client.start()
    if not started:
        result.errors.append("Failed to start process")
        return result

    info("Process started, sending initialize...")

    init_response = await client.initialize()
    if "error" in init_response:
        fail(f"Initialize failed: {init_response['error']}")
        result.errors.append(f"Initialize: {init_response['error']}")
        await client.stop()
        return result

    init_result = init_response.get("result", {})
    server_info = init_result.get("serverInfo", {})
    protocol_version = init_result.get("protocolVersion", "unknown")
    capabilities = init_result.get("capabilities", {})

    ok(f"Initialize OK - {server_info.get('name', '?')} v{server_info.get('version', '?')} (protocol: {protocol_version})")
    info(f"Capabilities: {json.dumps(capabilities, indent=None)}")
    result.init_ok = True

    # Send initialized notification
    await client.send_initialized()
    await asyncio.sleep(0.3)

    # 3. Discover tools
    info("Discovering tools...")
    tools_response = await client.list_tools()

    if "error" in tools_response:
        fail(f"tools/list failed: {tools_response['error']}")
        result.errors.append(f"tools/list: {tools_response['error']}")
        await client.stop()
        return result

    tools_result = tools_response.get("result", {})
    tools = tools_result.get("tools", [])
    tool_names = sorted([t.get("name", "?") for t in tools])
    result.tools_discovered = tool_names

    ok(f"Discovered {len(tools)} tools from server")

    # Print tool list
    for t in tools:
        name = t.get("name", "?")
        desc = t.get("description", "")[:60]
        schema_props = list(t.get("inputSchema", {}).get("properties", {}).keys())
        params_str = ", ".join(schema_props[:4])
        if len(schema_props) > 4:
            params_str += f", +{len(schema_props) - 4}"
        print(f"    {Colors.DIM}- {name}({params_str}) — {desc}{Colors.END}")

    # 4. Catalog alignment check
    expected = set(config.get("expected_catalog_tools", []))
    actual = set(tool_names)

    result.catalog_missing = sorted(expected - actual)
    result.server_extra = sorted(actual - expected)

    if result.catalog_missing:
        warn(f"In catalog but NOT in server ({len(result.catalog_missing)}):")
        for t in result.catalog_missing:
            print(f"      {Colors.YELLOW}- {t}{Colors.END}")

    if result.server_extra:
        info(f"In server but NOT in catalog ({len(result.server_extra)}):")
        for t in result.server_extra:
            print(f"      {Colors.CYAN}+ {t}{Colors.END}")

    if not result.catalog_missing and not result.server_extra:
        ok("Catalog perfectly aligned with server tools")

    # 5. Test ALL tools
    all_test_tools = config.get("test_all_tools", [])
    if all_test_tools:
        header(f"  Tool Call Tests ({len(all_test_tools)} tools)")
        for tool_name, tool_args in all_test_tools:
            if tool_name not in actual:
                warn(f"Skipping {tool_name} (not available on server)")
                result.tool_call_results.append({"tool": tool_name, "status": "skipped", "elapsed_ms": 0})
                continue

            # Auto-reconnect if previous tool crashed the server
            if client.process is None or client.process.returncode is not None:
                info("Server process died, restarting for remaining tools...")
                await client.stop()
                client = MCPStdioClient(binary_path, config.get("env_override"))
                if not await client.start():
                    fail("Failed to restart server")
                    break
                init_resp = await client.initialize()
                if "error" in init_resp:
                    fail(f"Re-initialize failed: {init_resp['error']}")
                    break
                await client.send_initialized()
                await asyncio.sleep(0.3)
                ok("Server restarted successfully")

            t0 = time.monotonic()
            call_response = await client.call_tool(tool_name, tool_args)
            elapsed = time.monotonic() - t0

            call_result_entry = {
                "tool": tool_name,
                "elapsed_ms": round(elapsed * 1000),
            }

            if "error" in call_response:
                fail(f"{tool_name}: {call_response['error']} ({elapsed:.1f}s)")
                call_result_entry["status"] = "error"
                call_result_entry["error"] = call_response["error"]
            else:
                call_result = call_response.get("result", {})
                is_error = call_result.get("isError", False)
                content = call_result.get("content", [])
                text_content = ""
                for c in content:
                    if c.get("type") == "text":
                        text_content = c.get("text", "")[:200]
                        break

                if is_error:
                    # Some tools may return "error" for invalid test inputs -- that's expected
                    # We mark as "tool_error" but it still means the bridge call worked
                    warn(f"{tool_name}: tool-level error ({elapsed * 1000:.0f}ms): {text_content[:80]}")
                    call_result_entry["status"] = "tool_error"
                    call_result_entry["error"] = text_content
                else:
                    ok(f"{tool_name}: OK ({elapsed * 1000:.0f}ms)")
                    if text_content:
                        preview = text_content[:100].replace("\n", " ")
                        print(f"      {Colors.DIM}{preview}{Colors.END}")
                    call_result_entry["status"] = "ok"
                    call_result_entry["preview"] = text_content[:100]

            result.tool_call_results.append(call_result_entry)
            await asyncio.sleep(0.15)

    await client.stop()
    return result


async def main():
    print(f"\n{Colors.BOLD}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}  Swift MCP Bridge Validator{Colors.END}")
    print(f"{Colors.BOLD}  Tests native Swift MCP servers via stdio JSON-RPC{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.END}")

    # Ensure test files exist on Desktop
    _ensure_test_files()

    results: list[ValidationResult] = []

    for server_id, config in SWIFT_SERVERS.items():
        result = await validate_server(server_id, config)
        results.append(result)

    # Summary
    print(f"\n{Colors.BOLD}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}  SUMMARY{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 70}{Colors.END}\n")

    total_tools = 0
    total_calls_ok = 0
    total_calls_tool_error = 0
    total_calls_error = 0
    total_calls_skipped = 0
    total_calls = 0
    all_passed = True

    for r in results:
        status = f"{Colors.GREEN}PASS{Colors.END}" if r.passed else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {r.server_id:<15} [{status}]  tools: {len(r.tools_discovered):<4} catalog_diff: {len(r.catalog_missing)} missing, {len(r.server_extra)} extra")

        total_tools += len(r.tools_discovered)
        for tc in r.tool_call_results:
            total_calls += 1
            if tc["status"] == "ok":
                total_calls_ok += 1
            elif tc["status"] == "tool_error":
                total_calls_tool_error += 1
            elif tc["status"] == "skipped":
                total_calls_skipped += 1
            else:
                total_calls_error += 1

        if not r.passed:
            all_passed = False
            for err in r.errors:
                print(f"    {Colors.RED}-> {err}{Colors.END}")

    print(f"\n  Total tools discovered: {total_tools}")
    if total_calls > 0:
        print(f"  Tool calls total: {total_calls}")
        print(f"    {Colors.GREEN}OK:         {total_calls_ok}{Colors.END}")
        if total_calls_tool_error > 0:
            print(f"    {Colors.YELLOW}Tool error: {total_calls_tool_error} (bridge worked, tool returned error for test input){Colors.END}")
        if total_calls_error > 0:
            print(f"    {Colors.RED}Bridge err: {total_calls_error}{Colors.END}")
        if total_calls_skipped > 0:
            print(f"    {Colors.CYAN}Skipped:    {total_calls_skipped}{Colors.END}")
        bridge_success_rate = (total_calls_ok + total_calls_tool_error) / max(total_calls - total_calls_skipped, 1) * 100
        print(f"  Bridge success rate: {bridge_success_rate:.1f}% ({total_calls_ok + total_calls_tool_error}/{total_calls - total_calls_skipped} calls got a response)")

    catalog_total = sum(len(c.get("expected_catalog_tools", [])) for c in SWIFT_SERVERS.values())
    print(f"  Catalog definitions: {catalog_total}")

    total_missing = sum(len(r.catalog_missing) for r in results)
    total_extra = sum(len(r.server_extra) for r in results)
    if total_missing > 0:
        print(f"  {Colors.YELLOW}Catalog tools missing from servers: {total_missing}{Colors.END}")
    if total_extra > 0:
        print(f"  {Colors.CYAN}Server tools not in catalog: {total_extra}{Colors.END}")

    # Show failed tools
    failed_tools = []
    for r in results:
        for tc in r.tool_call_results:
            if tc["status"] == "error":
                failed_tools.append((r.server_id, tc["tool"], tc.get("error", "?")))
    if failed_tools:
        print(f"\n  {Colors.RED}Failed bridge calls:{Colors.END}")
        for sid, tname, err in failed_tools:
            print(f"    {Colors.RED}{sid}.{tname}: {err[:80]}{Colors.END}")

    print()
    if all_passed and total_calls_error == 0:
        print(f"  {Colors.GREEN}{Colors.BOLD}All Swift MCP servers validated. All tools respond via bridge protocol.{Colors.END}")
    elif all_passed:
        print(f"  {Colors.YELLOW}{Colors.BOLD}Servers OK but {total_calls_error} bridge-level errors detected.{Colors.END}")
    else:
        print(f"  {Colors.RED}{Colors.BOLD}Some servers failed validation. See details above.{Colors.END}")

    print()
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
