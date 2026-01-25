# Оновлення Команди Встановлення Vibe CLI

**Дата**: 2026-01-25  
**Статус**: ✅ ЗАВЕРШЕНО

---

## 📋 ПРИЧИНА ОНОВЛЕННЯ

Офіційна документація Mistral змінилась:

**Джерело**: https://help.mistral.ai/en/articles/496007-get-started-with-mistral-vibe

**Нова офіційна команда:**
```bash
curl -LsSf https://mistral.ai/vibe/install.sh | bash
```

**Стара команда (застаріла):**
```bash
curl -fsSL https://get.vibe.sh | sh
```

---

## 🔧 ОНОВЛЕНІ ФАЙЛИ

### **1. src/brain/first_run_installer.py**

**Рядок 365:**
```python
# Install via official script (https://help.mistral.ai/en/articles/496007-get-started-with-mistral-vibe)
cmd = "curl -LsSf https://mistral.ai/vibe/install.sh | bash"
```

✅ Додано коментар з посиланням на офіційну документацію

---

### **2. src/brain/services_manager.py**

**Рядки 238-240:**
```python
# Using shell=True safely here as the command is hardcoded and trusted
# Official install: https://help.mistral.ai/en/articles/496007-get-started-with-mistral-vibe
result = subprocess.run(
    "curl -LsSf https://mistral.ai/vibe/install.sh | bash",
```

✅ Оновлено команду та додано коментар

---

### **3. scripts/setup_dev.py**

**Рядок 165:**
```python
print_info("Встановіть Vibe CLI: curl -LsSf https://mistral.ai/vibe/install.sh | bash")
```

✅ Оновлено повідомлення користувачу

---

### **4. requirements.txt**

**Рядок 15:**
```python
# mistral-vibe CLI встановлюється окремо: curl -LsSf https://mistral.ai/vibe/install.sh | bash
```

✅ Оновлено коментар

---

### **5. .docs/vibe_cli_analysis.md**

Оновлено всі згадки команди встановлення на офіційну:
- Рядок 33: Встановлення
- Рядок 73: Приклад у коді
- Рядок 106: Requirements.txt коментар
- Рядок 119: Інструкція користувачу
- Рядок 127: Документація
- Рядок 151: Встановлення (one-time)

✅ 6+ згадок оновлено

---

### **6. .docs/docker_removal_and_vibe_update.md**

Оновлено всі згадки:
- Рядок 33: Встановлення
- Рядок 51: Requirements.txt
- Рядок 145: setup_dev.py
- Рядок 196: Архітектура сервісів
- Рядок 218: Інструкція користувачу

✅ 5+ згадок оновлено

---

### **7. .docs/docker_functionality_analysis.md**

**Рядок 124:**
```markdown
- `vibe` (якщо встановлений через `curl -LsSf https://mistral.ai/vibe/install.sh | bash`)
```

✅ Оновлено

---

## 📊 ПІДСУМОК

| Файл | Змін | Статус |
|------|------|--------|
| `src/brain/first_run_installer.py` | 1 команда | ✅ |
| `src/brain/services_manager.py` | 1 команда + коментар | ✅ |
| `scripts/setup_dev.py` | 1 повідомлення | ✅ |
| `requirements.txt` | 1 коментар | ✅ |
| `.docs/vibe_cli_analysis.md` | 6+ згадок | ✅ |
| `.docs/docker_removal_and_vibe_update.md` | 5+ згадок | ✅ |
| `.docs/docker_functionality_analysis.md` | 1 згадка | ✅ |

**Всього файлів оновлено: 7**  
**Всього змін: 16+**

---

## ✅ РЕЗУЛЬТАТ

Вся система тепер використовує **офіційну команду Mistral**:

```bash
curl -LsSf https://mistral.ai/vibe/install.sh | bash
```

**Джерело**: https://help.mistral.ai/en/articles/496007-get-started-with-mistral-vibe

---

## 📝 ДЛЯ КОРИСТУВАЧІВ

Якщо ви вже встановили Vibe CLI старою командою - все працює нормально. Нова команда - це просто оновлена офіційна версія від Mistral.

**Перевірка встановлення:**
```bash
which vibe
vibe --version
```

**Готово!** ✅
