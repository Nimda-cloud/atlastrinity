# Configuration Templates

AtlasTrinity використовує централізовану систему шаблонів конфігурацій.

## Структура шаблонів

Всі template файли знаходяться в `config/`:

| Template | Призначення | Цільовий шлях після deploy |
|----------|-------------|----------------------------|
| `config.yaml.template` | Основні налаштування системи (агенти, voice, orchestrator) | `~/.config/atlastrinity/config.yaml` |
| `behavior_config.yaml.template` | Behavior Engine патерни, intent detection, tool routing | `~/.config/atlastrinity/behavior_config.yaml` |
| `mcp_servers.json.template` | MCP серверна конфігурація (маршрутизація серверів) | `~/.config/atlastrinity/mcp/config.json` |
| `vibe_config.toml.template` | Vibe MCP server конфігурація | `~/.config/atlastrinity/vibe_config.toml` |
| `monitoring_config.yaml.template` | Monitoring та metrics (Prometheus, Grafana, OpenSearch) | `~/.config/atlastrinity/monitoring_config.yaml` |

## Deployment Process

При виконанні `python scripts/setup_dev.py`:

1. Templates копіюються з `config/*.template` в `~/.config/atlastrinity/`
2. Environment variables розкриваються: `${HOME}`, `${CONFIG_ROOT}`, `${PROJECT_ROOT}`
3. Глобальні конфіги створюються лише якщо їх ще немає (first-time setup)
4. При необхідності можна форсувати overwrite через прапорці setup скрипта

## Редагування конфігурацій

### Для розробки:
- **Редагуйте templates** в `config/*.template`
- Запустіть `python scripts/setup_dev.py` щоб синхронізувати
- Або вручну копіюйте в `~/.config/atlastrinity/`

### Для production:
- **Редагуйте глобальні конфіги** безпосередньо в `~/.config/atlastrinity/`
- Templates використовуються лише як еталон

## Конфігураційна архітектура

### config.yaml (YAML)
Основні системні налаштування:
- Voice (STT/TTS)
- Agents (Atlas, Tetyana, Grisha)
- Orchestrator
- Security
- MCP connections

### behavior_config.yaml (YAML)
Behavior Engine - config-driven логіка:
- Adaptive behavior patterns
- Intent detection rules
- Tool routing configuration
- Task classification
- Strategy selection

### mcp_servers.json (JSON)
MCP серверна топологія:
- Список доступних серверів
- Tier prioritization (1-4)
- Agent-to-server assignments
- Connection params (timeouts, env vars)

### vibe_config.toml (TOML)
Vibe-specific налаштування:
- Active model
- Providers (Copilot, Mistral)
- Tool permissions
- MCP integrations

### monitoring_config.yaml (YAML)
Monitoring та metrics:
- Prometheus configuration
- Grafana settings
- OpenSearch integration
- Alerting rules

## Agent Protocols

**Location:** `src/brain/data/protocols/`

Операційні протоколи для внутрішніх агентів (Atlas, Tetyana, Grisha, Vibe):
- `create-new-program.md` - Створення нових проектів
- `self-healing-protocol.md` - Самолікування системи
- `vibe_docs.txt` - Vibe MCP documentation
- `data_protocol.txt` - Data processing rules
- `search_protocol.txt` - Search strategies
- `storage_protocol.txt` - Storage management
- `sdlc_protocol.txt` - Software development lifecycle
- `task_protocol.txt` - Task execution doctrine
- `system_mastery_protocol.txt` - System understanding
- `voice_protocol.txt` - Voice communication rules

**Завантаження:** Протоколи читаються через `src/brain/mcp_registry.py` при старті системи.  
**Використання:** Atlas, Tetyana, Grisha отримують протоколи через prompts (см. `src/brain/prompts/`).

**NOT to confuse with:** `.agent/workflows/` - це для Windsurf агента (редактор коду), НЕ для внутрішніх агентів.

## Чи об'єднувати конфіги?

**Рекомендація: НІ, залишити окремими**

### Переваги поточної структури:
✅ **Розділення concerns**: кожен конфіг має свою мету
✅ **Format optimization**: YAML для behavior patterns, JSON для MCP topology, TOML для Vibe
✅ **Independent evolution**: можна оновлювати behavior patterns незалежно від серверної топології
✅ **Tool compatibility**: Vibe очікує TOML, MCP manager очікує JSON
✅ **Size management**: behavior_config.yaml має 700+ ліній - об'єднання зробить конфіг величезним

### Коли варто об'єднувати:
❌ Якщо лише 1-2 невеликі конфіги
❌ Якби всі використовували однаковий формат
❌ Якщо часті конфлікти при синхронізації

**Висновок**: Поточна архітектура з 4 окремими конфігами **оптимальна** для проекту такого масштабу.

## Чи YAML описує повністю логіку системи?

### Так, ТЕПЕР повністю!

#### До рефакторингу:
- 300+ ліній hardcoded logic розкидано по 5 модулях
- Складно змінювати поведінку без редагування коду

#### Після рефакторингу:
✅ **Intent classification** - повністю в behavior_config.yaml (simple_chat, info_query, complex_task)
✅ **Tool routing** - всі правила в behavior_config.yaml (10 категорій, 100+ synonyms)
✅ **Task classification** - 16 типів задач в behavior_config.yaml
✅ **Strategy selection** - всі стратегії в behavior_config.yaml
✅ **Adaptive patterns** - всі behavior patterns в behavior_config.yaml
✅ **Server topology** - повна топологія в mcp_servers.json
✅ **Agent config** - моделі, параметри в config.yaml
✅ **Voice config** - STT/TTS в config.yaml

### Що ще залишилось в коді:
- **Execution logic** (як виконувати, а не що) - правильно залишається в коді
- **Error handling** - технічні деталі обробки помилок
- **API integrations** - низькорівнева робота з LLM APIs
- **State management** - orchestrator state machine (можна рефакторити далі, але не критично)

### Висновок:
**YAML тепер повністю описує DECISION LOGIC системи**. Вся поведінкова логіка (що робити, коли робити, як маршрутизувати) знаходиться в конфігах і може управлятися без редагування коду.

Лише execution деталі (як саме викликати API, як обробляти помилки) залишаються в Python коді, що є правильним підходом.
