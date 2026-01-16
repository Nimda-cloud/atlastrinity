# mcp-server-macos-use

Model Model Context Protocol (MCP) server in Swift. It allows controlling macOS applications by leveraging the accessibility APIs, primarily through the `MacosUseSDK`.

You can use it in Claude Desktop or other compatible MCP-client.

The server listens for MCP commands over standard input/output (`stdio`) and exposes several tools to interact with applications.

https://github.com/user-attachments/assets/b43622a3-3d20-4026-b02f-e9add06afe2b

## Complete List of Tools (39 Tools)

The server provides a comprehensive set of 39 tools for macOS automation, categorized below:

### 1. Application Management & Accessibility

- **`macos-use_open_application_and_traverse`**: Opens/activates an app and traverses its UI tree.
- **`macos-use_refresh_traversal`**: Re-scans the current app's UI tree without action.

### 2. Mouse & Keyboard Control

- **`macos-use_click_and_traverse`**: Left click at (x, y). Supports visual feedback.
- **`macos-use_type_and_traverse`**: Type text into the focused element.
- **`macos-use_press_key_and_traverse`**: Press specific keys (e.g., 'Return', 'Esc') with modifiers.
- **`macos-use_right_click_and_traverse`**: Right click (context menu).
- **`macos-use_double_click_and_traverse`**: Double click.
- **`macos-use_drag_and_drop_and_traverse`**: Drag from (x1, y1) to (x2, y2).
- **`macos-use_scroll_and_traverse`**: Scroll (up/down/left/right).

### 3. Window & System Management

- **`macos-use_window_management`**: Move, resize, minimize, maximize, or focus windows.
- **`macos-use_system_control`**: Media controls (volume, brightness, play/pause).
- **`macos-use_set_clipboard`**: Set clipboard text.
- **`macos-use_get_clipboard`**: Get clipboard text.
- **`macos-use_take_screenshot`**: Capture main screen (Base64 PNG). Alias: `screenshot`.
- **`macos-use_analyze_screen`**: Vision/OCR analysis of the screen content. Aliases: `ocr`, `analyze`.

### 4. Finder Integration (New)

- **`macos-use_finder_list_files`**: Lists files in the frontmost Finder window or a specified path.
- **`macos-use_finder_get_selection`**: Returns the POSIX paths of currently selected items in Finder.
- **`macos-use_finder_open_path`**: Opens a folder or file in Finder.
- **`macos-use_finder_move_to_trash`**: Moves the specified item to the Trash.

### 5. Native OS Integrations (Universal)

- **`macos-use_get_time`**: Get system time (supports timezones).
- **`macos-use_fetch_url`**: Fetch and parse website content (HTML -> Markdown).
- **`macos-use_run_applescript`**: Execute arbitrary AppleScript code.
- **`macos-use_spotlight_search`**: Fast file search using mdfind.
- **`macos-use_send_notification`**: Send primitive system notifications (via AppleScript).

### 6. Productivity Apps

- **Calendar**:
  - `macos-use_calendar_events`: List events.
  - `macos-use_create_event`: Create new events.
- **Reminders**:
  - `macos-use_reminders`: List incomplete reminders.
  - `macos-use_create_reminder`: Create tasks.
- **Notes**:
  - `macos-use_notes_list_folders`: List folders.
  - `macos-use_notes_create_note`: Create notes (HTML supported).
  - `macos-use_notes_get_content`: Read note content.
- **Mail**:
  - `macos-use_mail_send`: Send emails.
  - `macos-use_mail_read_inbox`: Read recent subjects/senders.

### 7. Discovery & Help

- **`macos-use_list_tools_dynamic`**: Returns a detailed structure describing all available tools and their schemas.

### 8. Terminal Command Execution

- **`execute_command`**: Execute a shell command (`/bin/zsh`). Alias: `terminal`. Maintains persistent CWD.

## Common Options

UI interaction tools accept these optional parameters:

- `showAnimation` (bool): Show a green indicator where the click happens.
- `animationDuration` (float): Speed of the animation.

## Building and Running

```bash
# Production build
swift build -c release

# Run
./.build/release/mcp-server-macos-use
```

## Privacy & Permissions

On first run, macOS will prompt for:
**Accessibility**, **Screen Recording**, **Calendar/Reminders**, and **Apple Events** (for AppleScript).
