# Grisha 3-Phase Verification Architecture

## Огляд

Grisha (Auditor/Visor) використовує **3-фазну архітектуру верифікації**, аналогічну до архітектури Тетяни, але адаптовану для аудиту та перевірки.

---

## Фаза 1: Планування Стратегії (Strategy Planning)

### Модель
- **strategy_model**: `raptor-mini` (deep reasoning)

### Завдання
1. Аналізує що потрібно перевірити виходячи з:
   - Опису кроку (`step.action`)
   - Очікуваного результату (`step.expected_result`)
   - Загального контексту завдання

2. Визначає **стратегію верифікації** (natural language):
   - Які аспекти потрібно перевірити
   - Які MCP інструменти можуть надати докази
   - Критерії успіху

### Вихід
Текстовий опис стратегії, наприклад:
```
Verification Strategy:
1. Check if file was created (filesystem tools)
2. Verify file contents match expected (read_file)
3. Confirm no errors in logs (vibe_check_db)
```

---

## Фаза 2: Виконання Інструментів (Tool Execution)

### Модель
- **model**: `gpt-4.1` (execution, аналогічно Тетяні)

### Завдання
1. На основі стратегії з Phase 1 підбирає **конкретні MCP tools**
2. Формує аргументи для tool calls
3. Виконує інструменти через MCP Manager
4. Збирає докази (evidence):
   - Логи з БД
   - Вміст файлів
   - Результати команд
   - Статус серверів

### Приклад Tool Calls
```python
# Based on strategy, executor calls:
- vibe.vibe_check_db(query="SELECT * FROM tool_executions WHERE step_id=...")
- filesystem.read_file(path="/path/to/file")
- macos-use.get_clipboard()
```

### Вихід
Список виконаних інструментів та їх результатів (evidence collection).

---

## Фаза 3: Формування Вердикту (Verdict Formation)

### Моделі
- **verdict_model**: `raptor-mini` (logical analysis)
- **vision_model**: `gpt-4o` (якщо потрібні скріншоти)

### Завдання
1. Аналізує зібрані докази з Phase 2:
   - Чи виконано очікуваний результат?
   - Чи є помилки?
   - Чи відповідає реальність плану?

2. Використовує **vision model** якщо потрібно:
   - Скріншоти для GUI задач
   - OCR для тексту на екрані

3. Формує **логічний вердикт**:
   - `verified: true/false`
   - `confidence: 0.0-1.0`
   - `description: <reasoning>`
   - `issues: [<list of problems>]`

### Fallback
Якщо `raptor-mini` не справляється або дає нестабільні результати, можна перемкнути:
```yaml
grisha:
  verdict_model: gpt-4.1  # Instead of raptor-mini
```

---

## Приклад Повного Flow

### Крок: "Створи файл config.json з налаштуваннями"

#### Phase 1: Strategy Planning (raptor-mini)
```
Input: step.action = "Create config.json file"
Output: 
  Strategy:
  1. Verify file exists (filesystem.list_directory)
  2. Check file contents are valid JSON (filesystem.read_file)
  3. Confirm no errors during creation (vibe.vibe_check_db)
```

#### Phase 2: Tool Execution (gpt-4.1)
```python
# Executor calls MCP tools:
tools_executed = [
  {"tool": "filesystem.list_directory", "args": {"path": "."}},
  {"tool": "filesystem.read_file", "args": {"path": "./config.json"}},
  {"tool": "vibe.vibe_check_db", "args": {"query": "SELECT * FROM logs WHERE step_id=5"}},
]

# Evidence collected:
evidence = {
  "file_exists": True,
  "file_contents": '{"key": "value"}',
  "errors": []
}
```

#### Phase 3: Verdict Formation (raptor-mini + gpt-4o)
```python
# Verdict LLM analyzes evidence:
verdict = {
  "verified": True,
  "confidence": 0.95,
  "description": "File config.json created successfully with valid JSON content",
  "issues": []
}
```

---

## Конфігурація Моделей

### Config.yaml
```yaml
grisha:
  # Phase 1: Strategy
  strategy_model: raptor-mini
  
  # Phase 2: Execution
  model: gpt-4.1
  
  # Phase 3: Verdict + Vision
  verdict_model: raptor-mini  # or gpt-4.1 as fallback
  vision_model: gpt-4o
```

### Провайдери
Всі моделі належать **Copilot provider**:
- `gpt-4.1` - Primary balanced model
- `gpt-4o` - Vision/multimodal, stable
- `raptor-mini` - Deep reasoning specialist
- `gpt-5-mini` - Fast lightweight
- `grok-mini-fast-1` - Very fast

**Виключення**: `devstral-2` (Mistral) - тільки для Vibe CLI, не для агентів.

---

## Переваги 3-Phase Architecture

1. **Чіткий розподіл відповідальностей**:
   - Strategy: думає що перевірити
   - Execution: збирає докази
   - Verdict: аналізує та виносить рішення

2. **Оптимізація витрат**:
   - Reasoning model (`raptor-mini`) тільки для логіки
   - Execution model (`gpt-4.1`) для tool calls
   - Vision model (`gpt-4o`) тільки коли потрібно

3. **Гнучкість**:
   - Можна змінювати моделі окремо для кожної фази
   - Fallback механізми для кожної фази
   - Можна додавати нові інструменти без зміни логіки

4. **Аналогія з Тетяною**:
   - Тетяна: Plan → Execute → Report
   - Grisha: Strategy → Execute → Verdict

---

## Sync Configuration

Для застосування змін у моделях:

```bash
# Sync templates to active configs
npm run config:sync

# Or with force overwrite
npm run config:sync -- --force
```

Скрипт синхронізує всі темплейти з `config/` до `~/.config/atlastrinity/`.
