# Vibe MCP → Electron Streaming Setup

## Архітектура стріму

```
┌─────────────┐
│  Vibe CLI   │ (subprocess з --output streaming)
└──────┬──────┘
       │ stdout/stderr через PTY
       ↓
┌─────────────────────┐
│ vibe_server.py      │
│ - read_stream()     │ → emit_log() через ctx.log()
│ - parse JSON lines  │
│ - format UI tags    │
└──────┬──────────────┘
       │ MCP LoggingMessageNotification
       ↓
┌─────────────────────┐
│ mcp_manager.py      │
│ - handle_log()      │ → викликає callbacks
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐
│ orchestrator.py     │
│ - _log()            │ → додає в state.logs[] + Redis pub/sub
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐
│ server.py           │
│ - GET /api/state    │ → повертає state з логами
└──────┬──────────────┘
       │ HTTP polling (кожну секунду)
       ↓
┌─────────────────────┐
│ App.tsx             │
│ - useEffect         │ → оновлює logs state
│ - pollState()       │
└──────┬──────────────┘
       │
       ↓
┌─────────────────────┐
│ ExecutionLog.tsx    │
│ - Відображає логи  │
│ - Підтримує теги:   │
│   🧠 [VIBE-THOUGHT] │
│   🔧 [VIBE-ACTION]  │
│   💬 [VIBE-GEN]     │
│   ⚡ [VIBE-LIVE]    │
└─────────────────────┘
```

## Формати повідомлень

### 1. JSON Streaming (від Vibe CLI)
```json
{"role": "assistant", "content": "Думаю про завдання..."}
{"role": "tool", "content": "Виконую команду: ls -la"}
```

### 2. Форматовані логи (в vibe_server.py)
```python
# assistant → 🧠 [VIBE-THOUGHT] ...
# tool → 🔧 [VIBE-ACTION] ...
# user → 💬 [VIBE-GEN] ...
# plain text → ⚡ [VIBE-LIVE] ...
```

### 3. UI фільтрація (в ExecutionLog.tsx)
```typescript
// Підтримує всі VIBE теги
log.message.includes('[VIBE-THOUGHT]') // синій колір
log.message.includes('[VIBE-ACTION]')  // зелений
log.message.includes('[VIBE-GEN]')     // жовтий
log.message.includes('[VIBE-LIVE]')    // білий
```

## Налаштування

### vibe_server.py - ключові зміни

1. **Стартове повідомлення:**
```python
await emit_log("info", f"🚀 [VIBE-LIVE] Запуск Vibe: {prompt[:80]}...")
```

2. **Стрім з форматуванням:**
```python
if obj["role"] == "assistant":
    message = f"🧠 [VIBE-THOUGHT] {preview}"
elif obj["role"] == "tool":
    message = f"🔧 [VIBE-ACTION] {preview}"
else:
    message = f"💬 [VIBE-GEN] {preview}"

await emit_log("info", message)
```

3. **Завершальне повідомлення:**
```python
await emit_log("info", "✅ [VIBE-LIVE] Vibe завершив роботу успішно")
```

### orchestrator.py - логування

```python
async def mcp_log_forwarder(message, source, level="info"):
    await self._log(message, source=source, type=level)
    
mcp_manager.register_log_callback(mcp_log_forwarder)
```

## Перевірка роботи

### 1. Зупинити всі процеси Vibe
```bash
./scripts/restart_vibe_clean.sh
```

### 2. Запустити Brain (якщо не запущений)
```bash
npm run dev
```

### 3. Моніторинг логів
```bash
# В окремому терміналі
./scripts/monitor_vibe.sh

# Або live моніторинг
./scripts/live_vibe_monitor.sh
```

### 4. Тест через UI
1. Відкрити Electron додаток
2. Викликати vibe_prompt через Brain
3. Спостерігати стрім в ExecutionLog панелі

## Приклад виводу в UI

```
⏰ 20:15:23 [VIBE_MCP] 🚀 [VIBE-LIVE] Запуск Vibe: Створи Python скрипт для...
⏰ 20:15:24 [VIBE_MCP] 🧠 [VIBE-THOUGHT] Аналізую вимоги до скрипта...
⏰ 20:15:25 [VIBE_MCP] 🔧 [VIBE-ACTION] Створюю файл project_stats.py
⏰ 20:15:26 [VIBE_MCP] 💬 [VIBE-GEN] Ось готовий скрипт...
⏰ 20:15:27 [VIBE_MCP] ✅ [VIBE-LIVE] Vibe завершив роботу успішно
```

## Troubleshooting

### Логи не з'являються в UI

1. **Перевірити Brain працює:**
```bash
curl http://127.0.0.1:8000/api/health
```

2. **Перевірити MCP сервер Vibe:**
```bash
ps aux | grep vibe_server
```

3. **Перевірити polling в браузері:**
- Відкрити DevTools → Network
- Шукати запити до `/api/state` кожну секунду

### Vibe процеси залипають

```bash
# Форсована зупинка
pkill -9 -f '/vibe -p'
pkill -9 -f 'vibe_runner'

# Перевірка
ps aux | grep vibe | grep -v grep
```

### Стрім не йде в реальному часі

Перевірити, що в `vibe_server.py`:
- `await emit_log()` викликається в `handle_line()`
- `ctx` передається правильно
- `logging_callback` зареєстрований в `ClientSession`

## Переваги поточної реалізації

✅ **Реал-тайм стрім** - логи з'являються миттєво  
✅ **Форматування** - кольори та іконки для різних типів  
✅ **Персистентність** - логи зберігаються в БД  
✅ **Фільтрація** - спам-фільтри для TUI артефактів  
✅ **Масштабованість** - через Redis pub/sub  
✅ **Відладка** - всі рівні логування доступні  

## Наступні кроки

1. ✅ Зупинити всі Vibe процеси
2. ✅ Налаштувати форматований вивід
3. ✅ Виправити помилки в коді
4. ⏳ Запустити Brain + Electron (npm run dev)
5. ⏳ Протестувати vibe_prompt виклик
6. ⏳ Перевірити стрім в UI

## Виправлені помилки

### 1. `NameError: name 'err_str' is not defined`
**Файл:** `src/brain/orchestrator.py`

**Проблема:** Змінна `err_str` використовувалась без визначення.

**Виправлення:**
```python
# Додано визначення змінної
err_str = str(last_error).lower()
is_logical_rejection = "grisha rejected" in err_str and any(
    k in err_str for k in ["підтвердження", "confirmation", ...]
)
```

### 2. `AttributeError: 'CallToolResult' object has no attribute 'get'`
**Файл:** `src/brain/agents/tetyana.py`

**Проблема:** Результат від MCP (`CallToolResult`) оброблявся як словник.

**Виправлення:**
```python
# Використання існуючого методу _format_mcp_result
v_res_raw = await self._call_mcp_direct("vibe", "vibe_analyze_error", {...})
v_res = self._format_mcp_result(v_res_raw) if v_res_raw else {}

# Тепер v_res - це словник і можна викликати .get()
if v_res.get("success"):
    ...
```

### 3. Вивід стріму в UI
**Файл:** `src/mcp_server/vibe_server.py`

**Зміни:**
- ✅ Додано стартове повідомлення: `🚀 [VIBE-LIVE] Запуск Vibe...`
- ✅ Форматування за ролями (assistant, tool, user)
- ✅ Завершальне повідомлення: `✅ [VIBE-LIVE] Vibe завершив роботу успішно`
- ✅ Фільтрація TUI артефактів `[2K`, `[1A`
