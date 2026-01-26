# Internal Agent Protocols

Ця папка містить протоколи для **внутрішніх агентів** AtlasTrinity (Atlas, Tetyana, Grisha, Vibe).

**НЕ плутати з:** `.agent/workflows/` - це для Windsurf агента (редактор коду).

---

## 📂 Структура

### Markdown Protocols (Detailed)
- `self-healing-protocol.md` - Автоматичне самолікування з Vibe + diagrams + GitHub
- `create-new-program.md` - Створення нових проектів/програм з нуля

### Text Protocols (Legacy Format)
- `data_protocol.txt` - Data handling guidelines
- `sdlc_protocol.txt` - Software Development Lifecycle
- `search_protocol.txt` - Search strategies
- `storage_protocol.txt` - Storage management
- `system_mastery_protocol.txt` - System mastery guidelines
- `task_protocol.txt` - Task management
- `voice_protocol.txt` - Voice interaction
- `vibe_docs.txt` - Vibe MCP documentation

---

## 🎯 Призначення

**Для кого:** Atlas, Tetyana, Grisha, Vibe (внутрішні агенти)

**Як використовуються:**
1. Агенти читають протоколи через `behavior_engine.py`
2. Протоколи визначають workflows та procedures
3. Координація між агентами (Atlas → Vibe → Tetyana → Grisha)

**Приклад:**
```python
# Atlas reads protocol
protocol = load_protocol("src/brain/data/protocols/create-new-program.md")

# Executes workflow
create_project_workflow(protocol)
```

---

## 🔄 Відмінність від .agent/workflows/

| Папка | Для кого | Призначення |
|-------|----------|-------------|
| `src/brain/data/protocols/` | Atlas, Tetyana, Grisha, Vibe | Internal agent coordination |
| `.agent/workflows/` | Windsurf (AI редактор) | Git setup, GitHub ops, integrity |

**Windsurf workflows (NOT here):**
- `.agent/workflows/github-operations.md` - GitHub token, commits
- `.agent/workflows/git-setup.md` - Git identity config
- `.agent/workflows/integrity.md` - Code integrity checks

---

## 📝 Configuration

Протоколи referenced в:
- `config/behavior_config.yaml.template`
- `src/brain/behavior_engine.py`

**Example reference:**
```yaml
# behavior_config.yaml.template
debugging:
  # Protocol: src/brain/data/protocols/self-healing-protocol.md
  vibe_debugging:
    enabled: true

project_creation:
  # Protocol: src/brain/data/protocols/create-new-program.md
  enabled: true
```

---

## ✅ Protocol Checklist

При додаванні нового протоколу:
1. ✅ Створити файл в `src/brain/data/protocols/`
2. ✅ Додати reference в `behavior_config.yaml.template`
3. ✅ Оновити цей README.md
4. ✅ Переконатися що агенти мають доступ
5. ✅ Не плутати з Windsurf workflows в `.agent/workflows/`

---

**Last Updated:** 2026-01-26  
**Maintained by:** AtlasTrinity Core Team  
**Agent Access:** Atlas, Tetyana, Grisha, Vibe
