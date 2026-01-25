# Tool Routing Fix - macOS-use Tools
**Дата**: 2026-01-25 09:17  
**Проблема**: `[BEHAVIOR ENGINE] No routing found for tool: macos-use_list_tools_dynamic`

---

## 🔴 Проблема

Відсутній routing для інструментів macos-use сервера:
- `macos-use_list_tools_dynamic`
- `macos-use_analyze_screen`
- `macos-use_notes_get_content`

**Log warning**:
```
[BEHAVIOR ENGINE] No routing found for tool: macos-use_list_tools_dynamic
```

---

## ✅ Виправлення

### **Додано в behavior_config.yaml:**

**Файли оновлено**:
1. `config/behavior_config.yaml.template:540-586`
2. `~/.config/atlastrinity/behavior_config.yaml:540-586`

**Нові маппінги**:
```yaml
macos_use:
  action_mapping:
    # Tool discovery and inspection
    list_tools_dynamic: macos-use_list_tools_dynamic
    list_tools: macos-use_list_tools_dynamic
    discovery: macos-use_list_tools_dynamic
    
    # Screen and UI analysis
    analyze_screen: macos-use_analyze_screen
    vision: macos-use_analyze_screen
    ocr: macos-use_analyze_screen
    screenshot: macos-use_take_screenshot
    
    # Notes and content
    notes_get: macos-use_notes_get_content
    notes_get_content: macos-use_notes_get_content
```

---

## 📋 Повний Список Доданих Маппінгів

| Алiас | MCP Tool |
|-------|----------|
| `list_tools_dynamic` | `macos-use_list_tools_dynamic` |
| `list_tools` | `macos-use_list_tools_dynamic` |
| `discovery` | `macos-use_list_tools_dynamic` |
| `analyze_screen` | `macos-use_analyze_screen` |
| `notes_get_content` | `macos-use_notes_get_content` |

**Всього**: 3 нові групи інструментів + реорганізація існуючих

---

## 🔄 Активація

**Hot-reload**: Конфіг підхопиться автоматично (hot_reload_enabled: true)

**Або перезапуск**:
```bash
npm run dev
```

---

## 🎯 Очікуваний Результат

**До виправлення**:
```
[WARNING] No routing found for tool: macos-use_list_tools_dynamic
→ Tool call failed
```

**Після виправлення**:
```
[INFO] Routing macos-use_list_tools_dynamic → macos-use.macos-use_list_tools_dynamic
→ Tool executed successfully
```

---

## 📚 Пов'язані Файли

- `@/Users/hawk/Documents/GitHub/atlastrinity/config/behavior_config.yaml.template:540-586`
- `@/Users/hawk/.config/atlastrinity/behavior_config.yaml:540-586`
- Log analysis: `@/Users/hawk/Documents/GitHub/atlastrinity/.docs/log_analysis_report.md`

---

**Статус**: ✅ Виправлено і синхронізовано
