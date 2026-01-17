# INSTRUCTIONS FOR VIBE AGENT

SYSTEM: You are the Senior Self-Healing Engineer for AtlasTrinity.
ROLE: Analyze and repair the Trinity runtime and its MCP servers.

CONTEXT:
- Project Root: /Users/olegkizyma/Documents/GitHub/atlastrinity
- Logs Directory: /Users/olegkizyma/.config/atlastrinity/logs
- OS: macOS
- Internal DB: PostgreSQL (Schema: sessions, tasks, task_steps, tool_executions, logs)
  - 'tool_executions' table contains RAW results of all agent actions.

ERROR MESSAGE:
Step ID: 1
Action: Use vibe_smart_plan to generate a development plan for a simple calculator application (UI, logic, error handling, testing). Specify Swift and SwiftUI for macOS as the preferred stack.

Grisha rejected: На скріншоті видно численні помилки запуску та логи перезапуску сервера Vibe, але немає жодного підтвердження, що інструмент vibe_smart_plan був успішно виконаний або що структурований план для Swift/SwiftUI калькулятора був згенерований. Відсутній як сам результат, так і його файл чи Markdown-структура у видимих директоріях або терміналі. Всі видимі логи стосуються помилок, завершення процесів та перезапуску, а не генерації плану. Issues: Відсутній результат виконання vibe_smart_plan., Видимі лише помилки та перезапуски серверів., Немає Markdown-файлу або структурованого плану у файловій системі чи терміналі.

TECHNICAL EXECUTION TRACE:
[
  {
    "tool_name": "vibe",
    "arguments": {
      "cwd": "/Users/olegkizyma/AtlasProjects",
      "prompt": "Generate a detailed, structured development plan for a simple calculator application. The plan must cover: 1) UI design (using SwiftUI for macOS), 2) Core calculation logic (in Swift), 3) Error handling (invalid input, division by zero), 4) Testing (unit tests for logic and UI). Output the plan in Markdown format with clear sections and bullet points. Preferred stack: Swift and SwiftUI for macOS. Ensure the result is saved and available for verification.",
      "step_id": "1",
      "timeout_s": 3600,
      "output_format": "markdown"
    },
    "result": ""
  },
  {
    "tool_name": "vibe",
    "arguments": {
      "cwd": "/Users/olegkizyma/AtlasProjects",
      "step_id": "1",
      "language": "Swift",
      "platform": "macOS",
      "sections": [
        "UI Design",
        "Core Logic",
        "Error Handling",
        "Testing"
      ],
      "timeout_s": 3600,
      "description": "Generate a structured development plan for a simple calculator application targeting macOS, using Swift and SwiftUI. The plan should cover UI design, core logic, error handling (including invalid input and division by zero), and testing (unit tests for logic and UI interactions). Output the plan in a structured format (Markdown or JSON) with clear sections for each aspect.",
      "ui_framework": "SwiftUI",
      "output_format": "markdown",
      "project_title": "Simple Calculator Application"
    },
    "result": ""
  },
  {
    "tool_name": "vibe",
    "arguments": {
      "cwd": "/Users/olegkizyma/AtlasProjects",
      "step_id": "1",
      "timeout_s": 3600,
      "components": [
        "User Interface (UI)",
        "Calculation Logic",
        "Error Handling",
        "Testing"
      ],
      "technology_stack": "Swift, SwiftUI for macOS",
      "project_description": "Develop a simple calculator application for macOS. The app should have a user interface for inputting numbers and operations, core logic for arithmetic calculations, error handling (including invalid input and division by zero), and unit testing for both logic and UI interactions."
    },
    "result": ""
  }
]

RECENT LOGS:
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (145s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (150s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (155s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (160s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (165s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (170s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (175s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (180s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (185s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (190s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (195s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (200s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (205s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (210s silence)
[VIBE] ⏳ [VIBE-LIVE] Vibe is processing... (215s silence)
[SYSTEM] Preparing verification...
[GRISHA] Результат не підтверджено. План не згенеровано, видно лише помилки та перезапуск серверів.
[WARNING] Step 1 Attempt 3 failed: Grisha rejected: На скріншоті видно численні помилки запуску та логи перезапуску сервера Vibe, але немає жодного підтвердження, що інструмент vibe_smart_plan був успішно виконаний або що структурований план для Swift/SwiftUI калькулятора був згенерований. Відсутній як сам результат, так і його файл чи Markdown-структура у видимих директоріях або терміналі. Всі видимі логи стосуються помилок, завершення процесів та перезапуску, а не генерації плану. Issues: Відсутній результат виконання vibe_smart_plan., Видимі лише помилки та перезапуски серверів., Немає Markdown-файлу або структурованого плану у файловій системі чи терміналі.
[ORCHESTRATOR] Atlas Recovery for Step 1...
[ATLAS] Крок 1 зупинився. Шукаю рішення.

INSTRUCTIONS:
1. Analyze the error thoroughly using logs and source code.
2. Identify the root cause.
3. ACTIVELY FIX the issue (edit code, run commands).
4. If you modify Swift code in 'vendor/mcp-server-macos-use', you MUST recompile it by running 'swift build -c release' in that directory.
5. After any fix to an MCP server, use 'vibe_restart_mcp_server(server_name)' to apply changes.
6. Verify the fix works.
7. Provide a detailed summary.