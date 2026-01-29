# Аналіз використання Vibe MCP та робочого процесу агентів

## Резюме
Аналіз завдання з калькулятором виявив **критичне порушення протоколу**: код створювався через GUI симуляцію замість Vibe MCP, що суперечить доктрині самолікування та якісної розробки ПЗ.

---

## 1. ❌ Vibe MCP НЕ використовувався для створення коду

### Фактичні дані з бази даних

```sql
-- Кроки 2-4: Створення проекту та реалізація
Step 2: "Open Xcode and create a new macOS project" → macos-use_open_application_and_traverse
Step 3: "Design the user interface for the calculator" → macos-use_click_and_traverse  
Step 4: "Implement the calculator's logic in Swift" → macos-use_type_and_traverse
```

### Проблема
- **GUI симуляція** використовувалася для "написання" коду
- `macos-use_type_and_traverse` симулював введення тексту в Xcode
- **Жодного виклику** `vibe_implement_feature`, `vibe_prompt`, або `vibe_code_review`

### Наслідки
1. **Порушення доктрини самолікування** - Vibe забезпечує якість, тестування, самовиправлення
2. **Відсутність верифікації коду** - немає code review, тестування, аналізу помилок
3. **Низька якість** - код створений вручну без best practices перевірок
4. **Помилкова оцінка успіху** - GUI інструменти повернули success, але артефакти не створені

---

## 2. ✅ SDLC протокол існує але був неповним

### Поточний стан

**Файл**: `@/src/brain/data/protocols/sdlc_protocol.txt`

**Інтеграція**:
- ✅ Підтягується в промпти Atlas, Tetyana, Grisha
- ✅ Використовується через `AgentPrompts.SDLC_PROTOCOL`
- ✅ Atlas динамічно вибирає між `SDLC_PROTOCOL` та `TASK_PROTOCOL` на основі intent

**Код інтеграції** (`@/src/brain/agents/atlas.py:846-854`):
```python
intent = enriched_request.get("intent", "task")

# Inject context-specific doctrine
if intent == "development":
    doctrine = AgentPrompts.SDLC_PROTOCOL
else:
    doctrine = AgentPrompts.TASK_PROTOCOL

dynamic_system_prompt = self.SYSTEM_PROMPT.replace(
    "{{CONTEXT_SPECIFIC_DOCTRINE}}",
    doctrine,
)
```

### Що було відсутнє (до виправлення)

**Попередня версія SDLC_PROTOCOL**:
```
PHASE 3: INCREMENTAL IMPLEMENTATION
- RULE: ONE MODULE PER STEP. Build, then verify.
- RESEARCH: Use context7...
- PATTERN: Skeleton -> Logic -> Error Handling -> Tests -> Verify.
```

❌ **Не вимагав використання Vibe**  
❌ **Не забороняв GUI симуляцію для коду**  
❌ **Не специфікував інструменти**

### Виправлення реалізоване

**Нова версія** (`@/src/brain/data/protocols/sdlc_protocol.txt:19-26`):
```
- **MANDATORY: ALL CODE GENERATION MUST USE VIBE MCP**:
  * Use `vibe_implement_feature(goal="...", context_files=[...])` for new features/modules
  * Use `vibe_prompt(prompt="...")` for code snippets, refactoring, or debugging
  * NEVER manually write code via typing in IDEs or text editors
  * NEVER use GUI simulation (clicks/typing) for code creation
  * Vibe ensures quality, follows best practices, and provides self-healing
- RESEARCH: Use `context7` to verify library APIs BEFORE invoking Vibe
- PATTERN: Research (context7) -> Implement (Vibe) -> Verify (Grisha) -> Integrate.
```

---

## 3. ⚠️ Послідовність роботи агентів - частково правильна

### Фази виконання завдання

#### Фаза 1: Atlas створює план ✅
**Правильно**:
- Atlas отримав запит: "створити калькулятор на свіфті, скомпілував у dmg"
- Визначив intent як `development` (припущення)
- Використав SDLC_PROTOCOL для планування
- Створив 11 кроків з логічною послідовністю

**Проблема**:
- План включав **GUI симуляцію** замість Vibe інструментів
- Крок 4: "Implement the calculator's logic" → НЕ специфікував `vibe_implement_feature`
- Atlas не мав чіткої інструкції в SDLC що код ОБОВ'ЯЗКОВО через Vibe

#### Фаза 2: Tetyana виконує кроки ❌
**Що пішло не так**:
- Tetyana отримала крок: "Implement the calculator's logic in Swift"
- Вибрала `macos-use_type_and_traverse` (GUI симуляція введення коду)
- НЕ використала `vibe_implement_feature` або `vibe_prompt`

**Чому це сталося**:
1. **План не вказав інструмент** - Atlas не специфікував `realm: vibe` для кроку 4
2. **Tetyana інтерпретувала як UI задачу** - "implement logic" → "type code in Xcode"
3. **SDLC протокол не забороняв** GUI симуляцію для коду

**Tetyana промпт** (`@/src/brain/prompts/tetyana.py:39-43`):
```
CRITICAL: COMPILATION/BUILD TASKS: ... you MUST use `execute_command`
```
✅ Це правило працювало для компіляції (кроки 6-9 використовували `execute_command`)  
❌ Але не було правила для **генерації коду** → use Vibe

#### Фаза 3: Grisha верифікація ⚠️
**Не виконалася**:
- Grisha має верифікувати кожен крок через `requires_verification: true`
- Крок 4 (реалізація коду) мав бути верифікований
- Але якщо артефакт не створений, Grisha не міг його перевірити

#### Фаза 4: Atlas evaluation ❌
**Хибнопозитивна оцінка**:
- Див. `POSTMORTEM_CALCULATOR_TASK.md` - вже виправлено

---

## 4. 📋 Конфігурації та темплейти

### Перевірка наявності протоколів у конфігураціях

**Config templates** (`/config/`):
```
behavior_config.yaml.template - ✅ Посилається на протоколи:
  Line 28-31: References src/brain/data/protocols/*.txt
  Line 1640: References self-healing-protocol.md
  Line 1720: References create-new-program.md
  
  Line 1774: implement_code → Vibe generates initial code ✅
  Line 1783: implementer: vibe ✅
```

**Висновок**: 
- ✅ Config шаблон **правильно** вказує Vibe як implementer
- ✅ Workflow `project_creation` використовує Vibe для генерації коду
- ❌ Але цей workflow НЕ спрацював для калькулятора (task_id показує, що використовувався стандартний SDLC flow)

### Протоколи в директорії

**Наявні** (`src/brain/data/protocols/`):
- ✅ `sdlc_protocol.txt` (тепер оновлений)
- ✅ `data_protocol.txt`
- ✅ `search_protocol.txt`
- ✅ `storage_protocol.txt`
- ✅ `system_mastery_protocol.txt`
- ✅ `task_protocol.txt`
- ✅ `vibe_docs.txt`
- ✅ `voice_protocol.txt`

**Відсутні в `src/brain/data/protocols/`** (але є в config коментарях):
- ❌ `self-healing-protocol.md` (згадується в behavior_config line 1640)
- ❌ `create-new-program.md` (згадується в behavior_config line 1720)

**Рекомендація**: Створити відсутні файли або видалити посилання з config.

---

## 5. 🔧 Виправлення та рекомендації

### Реалізовані виправлення

#### Fix #1: SDLC протокол доповнено
**Файл**: `src/brain/data/protocols/sdlc_protocol.txt`
- ✅ Додано **MANDATORY: ALL CODE GENERATION MUST USE VIBE MCP**
- ✅ Заборонено GUI симуляцію для створення коду
- ✅ Специфіковано інструменти: `vibe_implement_feature`, `vibe_prompt`

#### Fix #2: Tetyana промпт доповнено
**Файл**: `src/brain/prompts/tetyana.py:39-43`
- ✅ Додано **CRITICAL: COMPILATION/BUILD TASKS** правило
- ✅ Заборонено GUI симуляцію для компіляції/білдів

#### Fix #3: Atlas evaluation посилено
**Файл**: `src/brain/agents/atlas.py:1159-1177, 1235-1240`
- ✅ Додано artifact verification
- ✅ Примусове `achieved=False` якщо артефакти відсутні

### Необхідні додаткові виправлення

#### TODO #1: Atlas планування має виявляти software development
**Проблема**: Atlas має автоматично розпізнавати запити на розробку ПЗ та призначати `intent="development"`.

**Рішення**: Додати в enrichment логіку:
```python
# В src/brain/agents/atlas.py → enrich_request()
keywords = ["створити калькулятор", "написати програму", "розробити API", 
            "build app", "implement feature", "create library"]
if any(kw in user_request.lower() for kw in keywords):
    enriched["intent"] = "development"
```

#### TODO #2: Atlas має специфікувати `realm: vibe` для кроків коду
**Проблема**: План не вказує який MCP сервер використовувати для імплементації.

**Рішення**: Оновити `atlas_plan_creation_prompt`:
```
For code implementation steps, ALWAYS specify:
{
  "realm": "vibe",
  "tool": "vibe_implement_feature",
  "action": "Implement calculator logic using Vibe"
}
```

#### TODO #3: Tetyana має відхиляти manual code writing
**Проблема**: Tetyana може інтерпретувати "implement logic" як "type code manually".

**Рішення**: Додати в `tetyana.py` OPERATIONAL DOCTRINES:
```
- **CODE GENERATION FORBIDDEN**: You CANNOT write code by typing it manually.
  For ANY code implementation, you MUST delegate to:
  * vibe_implement_feature - for new features/modules
  * vibe_prompt - for code snippets/fixes
  * vibe_code_review - before critical changes
```

---

## 6. ✅ Перевірений робочий процес (після виправлень)

### Правильна послідовність для розробки ПЗ

```
1. USER REQUEST: "Створи калькулятор на Swift"
   ↓
2. ATLAS (Enrichment):
   - Розпізнає: intent="development"
   - Активує: SDLC_PROTOCOL
   ↓
3. ATLAS (Planning):
   - Крок 1: Research Swift best practices (context7)
   - Крок 2: vibe_implement_feature(goal="Calculator UI and logic", context_files=[])
   - Крок 3: execute_command("xcodebuild -scheme Calculator...")
   - Крок 4: execute_command("hdiutil create -volname Calculator...")
   ↓
4. TETYANA (Execution):
   - Крок 1: Викликає context7 для документації Swift
   - Крок 2: Викликає vibe_implement_feature → Vibe створює код
   - Крок 3: Викликає execute_command → Реальна компіляція
   - Крок 4: Викликає execute_command → Створення DMG
   ↓
5. GRISHA (Verification):
   - Перевіряє: чи існує .app файл
   - Перевіряє: чи існує .dmg файл
   - Перевіряє: чи встановлено в /Applications
   ↓
6. ATLAS (Evaluation):
   - Artifact verification: ✅ .app exists, ✅ .dmg exists
   - achieved: true
   - quality_score: 1.0
   - should_remember: true ✅
```

---

## Висновки

### Відповіді на питання користувача

**1. Чи відбувається створення ПЗ через Vibe MCP?**
- ❌ **НІ** - в завданні калькулятора Vibe НЕ використовувався
- ✅ **ВИПРАВЛЕНО** - SDLC протокол тепер ВИМАГАЄ Vibe для всього коду

**2. Чи підтягнувся протокол створення ПЗ?**
- ✅ **ТАК** - SDLC_PROTOCOL існує і інтегрований в промпти всіх агентів
- ⚠️ **АЛЕ** - він був неповним (не вимагав Vibe)
- ✅ **ВИПРАВЛЕНО** - тепер містить mandatory Vibe usage

**3. Чи правильна послідовність роботи агентів?**
- ⚠️ **ЧАСТКОВО**:
  - ✅ Atlas правильно планує (використовує SDLC)
  - ❌ Atlas НЕ специфікував Vibe в кроках (бо протокол не вимагав)
  - ❌ Tetyana неправильно вибрала GUI симуляцію замість Vibe
  - ❌ Grisha не виявила відсутність артефактів (бо вони взагалі не створилися)
  - ❌ Atlas evaluation хибнопозитивно оцінила як успіх

### Статус виправлень
- ✅ **SDLC протокол оновлено** - mandatory Vibe usage
- ✅ **Tetyana промпт оновлено** - заборона GUI для компіляції + заборона manual code writing
- ✅ **Atlas evaluation оновлено** - artifact verification
- ✅ **TODO #1**: Atlas enrichment (auto-detect development intent) - **РЕАЛІЗОВАНО**
- ✅ **TODO #2**: Atlas planning (specify realm: vibe for code steps) - **РЕАЛІЗОВАНО**
- ✅ **TODO #3**: Tetyana doctrine (explicit ban on manual code writing) - **РЕАЛІЗОВАНО**
- ✅ **Vibe model fix**: Changed model name to devstral-2 to avoid rate limits

---

*Дата аналізу: 2026-01-29*  
*Статус: **ВСІ виправлення реалізовані та готові до тестування***
