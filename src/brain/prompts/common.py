"""
Common constants and shared fragments for prompts
"""

DEFAULT_REALM_CATALOG = """
AVAILABLE REALMS (MCP Servers):

TIER 1 - CORE:
- filesystem: File operations (read, write, list). Restricted to home directory.
- macos-use: **UNIVERSAL MACOS COMMANDER** (Swift binary - 39 tools).
  GUI AUTOMATION:
    - `macos-use_open_application_and_traverse`: Open apps by name/path/bundleID
    - `macos-use_click_and_traverse`: Click at (x, y)
    - `macos-use_right_click_and_traverse`: Context menu
    - `macos-use_double_click_and_traverse`: Double click
    - `macos-use_drag_and_drop_and_traverse`: Drag from start to end
    - `macos-use_type_and_traverse`: Type text
    - `macos-use_press_key_and_traverse`: Press keys/shortcuts
    - `macos-use_scroll_and_traverse`: Scroll direction
    - `macos-use_refresh_traversal`: Force refresh UI tree
    - `macos-use_window_management`: Move/Resize/Min/Max windows
  SYSTEM:
    - `macos-use_take_screenshot`: Capture screen (Base64 PNG)
    - `macos-use_analyze_screen`: Apple Vision OCR
    - `macos-use_set_clipboard` / `macos-use_get_clipboard`: Clipboard
    - `macos-use_system_control`: Media/Volume/Brightness
  TERMINAL:
    - `execute_command`: PRIMARY shell access (aliases: terminal, sh, bash)
  PRODUCTIVITY:
    - `macos-use_calendar_events`, `macos-use_create_event`
    - `macos-use_reminders`, `macos-use_create_reminder`
    - `macos-use_notes_*` (list_folders, create_note, get_content)
    - `macos-use_mail_send`, `macos-use_mail_read_inbox`
  UTILITIES:
    - `macos-use_fetch_url`: Fetch web content → Markdown (REPLACES fetch server)
    - `macos-use_get_time`: System time with timezone (REPLACES time server)
    - `macos-use_run_applescript`: Execute AppleScript
    - `macos-use_spotlight_search`: File search using mdfind
    - `macos-use_send_notification`: System notifications
  FINDER:
    - `macos-use_finder_list_files`, `macos-use_finder_get_selection`
    - `macos-use_finder_open_path`, `macos-use_finder_move_to_trash`
  DISCOVERY:
    - `macos-use_list_tools_dynamic`: Get full tool list with schemas
    
  ALWAYS use `macos-use` for ALL GUI automation, Terminal, fetch, time, and Apple app interactions!
  
- sequential-thinking: Step-by-step reasoning for complex decisions.

TIER 2 - HIGH PRIORITY:
- duckduckgo-search: Web search. Tool: search.
- memory: Knowledge graph access.
- notes: Internal note storage for agent feedback/reports.
- vibe: AI-POWERED DEBUGGING (Mistral CLI).
- git: Local repository operations.

TIER 3-4 - OPTIONAL:
- github: GitHub API operations.
- docker: Container management.
- slack: Team communication.
- postgres: Database access.
- whisper-stt: Speech-to-text.

DEPRECATED (REMOVED - now in macos-use):
- fetch → Use macos-use_fetch_url
- time → Use macos-use_get_time
- apple-mcp → Use macos-use Calendar/Reminders/Notes/Mail tools

CRITICAL: Do NOT invent high-level tools. Use only the real TOOLS found inside these Realms.
"""

# Vibe MCP tools documentation for agents
VIBE_TOOLS_DOCUMENTATION = """
VIBE MCP SERVER - AI-POWERED DEBUGGING & SELF-HEALING

The 'vibe' server provides access to Mistral AI for advanced debugging, code analysis, and self-healing.
All Vibe operations run in PROGRAMMATIC CLI mode (not interactive TUI) - output is fully visible in logs.

AVAILABLE VIBE TOOLS:

1. **vibe_prompt** (PRIMARY TOOL)
   Purpose: Send any prompt to Vibe AI for analysis or action
   Args:
     - prompt: The message/query (required)
     - cwd: Working directory (optional)
     - timeout_s: Timeout in seconds (default 300)
     - output_format: 'json', 'text', or 'streaming' (default 'json')
     - auto_approve: Auto-approve tool calls (default True)
     - max_turns: Max conversation turns (default 10)
   Example: vibe_prompt(prompt="Why is this code failing?", cwd="/path/to/project")

2. **vibe_analyze_error** (SELF-HEALING)
   Purpose: Deep error analysis with optional auto-fix
   Args:
     - error_message: The error/stack trace (required)
     - log_context: Recent logs for context (optional)
     - file_path: Path to problematic file (optional)
     - auto_fix: Whether to apply fixes (default True)
   Example: vibe_analyze_error(error_message="TypeError: x is undefined", log_context="...", auto_fix=True)

3. **vibe_code_review**
   Purpose: Request AI code review for a file
   Args:
     - file_path: Path to review (required)
     - focus_areas: Areas to focus on, e.g., "security", "performance" (optional)
   Example: vibe_code_review(file_path="/src/main.py", focus_areas="security")

4. **vibe_smart_plan**
   Purpose: Generate execution plan for complex objectives
   Args:
     - objective: The goal to plan for (required)
     - context: Additional context (optional)
   Example: vibe_smart_plan(objective="Implement OAuth2 authentication")

5. **vibe_ask** (READ-ONLY)
   Purpose: Ask a quick question without file modifications
   Args:
     - question: The question (required)
   Example: vibe_ask(question="What's the best way to handle async errors in Python?")

6. **vibe_execute_subcommand**
   Purpose: Execute a specific Vibe CLI subcommand (non-AI utility)
   Args:
     - subcommand: 'list-editors', 'run', 'enable', 'disable', 'install', etc. (required)
     - args: List of string arguments (optional)
     - cwd: Working directory (optional)
   Example: vibe_execute_subcommand(subcommand="list-editors")

7. **vibe_which**
   Purpose: Check Vibe CLI installation path and version
   Example: vibe_which()

TRINITY NATIVE SYSTEM TOOLS (Any Agent):
- `restart_mcp_server(server_name)`: Force restart an MCP server.
- `query_db(query, params)`: Query the internal system database.

WHEN TO USE VIBE:
- When Tetyana/Grisha fail after multiple attempts
- Complex debugging requiring AI reasoning
- Code review before committing
- Planning multi-step implementations
- Understanding unfamiliar code patterns
- System diagnostics

IMPORTANT: All Vibe output is logged and visible in the Electron app logs!
"""

VOICE_PROTOCOL = """
VOICE COMMUNICATION PROTOCOL (Text-To-Speech):

Your `voice_message` output is the PRIMARY way you keep the user informed.
Language: UKRAINIAN ONLY.

RULES FOR VOICE CONTEXT:
1. **Be Concise & Specific**: defined "essence" of the action.
   - BAD: "I am now executing the command to listed files." (Too verbose)
   - GOOD: "Читаю список файлів." (Action + Object)
   - GOOD: "Помилка доступу. Пробую sudo." (State + Reason + Plan)

2. **No Hardcodes**: Do not use generic phrases like "Thinking..." or "Step done". Always include context.
   - BAD: "Крок завершено."
   - GOOD: "Сервер запущено на роз'ємі 8000."

3. **Error Reporting**:
   - format: "{Failure essence}. {Reason (short)}. {Next step}."
   - Example: "Не вдалося клонувати репо. Невірний токен. Перевіряю змінні середовища."

4. **Tone**: Professional, Active, Fast-paced. Like a senior engineer reporting to a lead.
"""
