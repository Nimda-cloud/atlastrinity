# Vendor Directory

Ця директорія містить сторонні MCP сервери, які компілюються локально.

## mcp-server-macos-use (Swift)

**Статус**: Кастомний Swift MCP сервер для macOS контролю

### Опис
Універсальний Swift-based MCP сервер з 35+ інструментами для контролю macOS:
- GUI automation через Accessibility API
- Vision/OCR для аналізу екрану
- Terminal commands
- Fetch URL, Time utilities
- AppleScript execution
- Calendar, Reminders, Notes, Mail
- Finder, Spotlight, Notifications

### Налаштування

1. **Якщо код відсутній**:
   Код має бути доданий вручну або як git submodule. Структура:
   ```
   vendor/
   └── mcp-server-macos-use/
       ├── Package.swift
       ├── Sources/
       │   └── [Swift source files]
       └── .build/
           └── release/
               └── mcp-server-macos-use (binary)
   ```

2. **Компіляція**:
   ```bash
   cd vendor/mcp-server-macos-use
   swift build -c release
   ```

3. **Перевірка**:
   ```bash
   ls -lh vendor/mcp-server-macos-use/.build/release/mcp-server-macos-use
   ```

### Використання в конфігурації

У `config/mcp_servers.json.template`:
```json
{
  "macos-use": {
    "command": "${PROJECT_ROOT}/vendor/mcp-server-macos-use/.build/release/mcp-server-macos-use",
    "tier": 1,
    "description": "Universal macOS control (35+ tools)"
  }
}
```

### Примітки

- Бінарний файл `.build/` ігнорується в git (див. `.gitignore`)
- Потрібен Swift 5.9+ та macOS 13.0+
- Необхідні дозволи: Accessibility, Screen Recording
- Компіляція займає ~1-2 хвилини при першому запуску
