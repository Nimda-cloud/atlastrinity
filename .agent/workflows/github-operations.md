---
description: GitHub repository operations using GITHUB_TOKEN from .env
---

# GitHub Operations Workflow

## Загальні правила роботи з GitHub

### 🔐 Автентифікація

**КРИТИЧНО**: Всі операції з віддаленим репозиторієм GitHub **ЗАВЖДИ** мають використовувати `GITHUB_TOKEN` з файлу `.env`.

### 1. Налаштування Git Remote з токеном (обов'язково перед роботою)

// turbo
```zsh
export GITHUB_TOKEN=$(grep GITHUB_TOKEN .env | cut -d'=' -f2 | tr -d '\r\n') && \
git remote set-url origin https://$GITHUB_TOKEN@github.com/Nimda-cloud/atlastrinity.git && \
echo "✅ Git remote configured with GITHUB_TOKEN from .env"
```

**Чому це потрібно**: Без цього git буде запитувати username/password при push/pull операціях.

### 2. Перевірка налаштувань

```zsh
git remote -v
```

**Очікуваний результат**: URL має містити токен у форматі:
```
origin  https://ghp_xxxxxxxxxxxxx@github.com/Nimda-cloud/atlastrinity.git
```

### 3. Стандартний Git Workflow

#### Перед початком роботи:
```zsh
# 1. Переконатись що remote налаштовано
git remote -v

# 2. Отримати останні зміни
git pull origin main
```

#### Під час роботи:
```zsh
# 1. Перевірити статус
git status

# 2. Додати зміни
git add .

# 3. Зробити коміт
git commit -m "feat: опис змін"

# 4. Відправити на GitHub
git push origin main
```

## 🔒 Правила безпеки

### ЗАБОРОНЕНО ❌

1. **Ніколи не коммітити `.env` файл** - він у `.gitignore`
2. **Ніколи не писати токен у код або конфігурацію** - тільки з `.env`
3. **Ніколи не виводити токен у логи** або консоль
4. **Ніколи не використовувати токен у відкритому вигляді** в командах, які можуть потрапити в історію

### ОБОВ'ЯЗКОВО ✅

1. **Завжди перевіряти** що `.env` є у `.gitignore`
2. **Завжди використовувати** змінні оточення для токену
3. **Завжди очищати** змінну `$GITHUB_TOKEN` після використання (або вона очиститься після закриття сесії)

## 🤖 GitHub Actions

### Секрети для Actions

У GitHub репозиторії налаштовані такі секрети:
- `GITHUB_TOKEN` - автоматично надається GitHub Actions
- `COPILOT_API_KEY` - для Copilot інтеграції
- `MISTRAL_API_KEY` - для AI функціоналу
- `OPENROUTER_API_KEY` - для OpenRouter API
- `VISION_API_KEY` - для Vision моделей
- `GOOGLE_MAPS_API_KEY` - для Google Maps (backend)
- `VITE_GOOGLE_MAPS_API_KEY` - для Google Maps (frontend/Vite)
- `WINDSURF_API_KEY` - для Windsurf/Codeium провайдера
- `WINDSURF_INSTALL_ID` - Installation ID Windsurf
- `WINDSURF_LS_CSRF` - Windsurf Language Server CSRF
- `WINDSURF_LS_PORT` - Windsurf Language Server порт
- `WINDSURF_MODEL` - модель Windsurf
- `REDIS_URL` - URL Redis сервера
- `LOG_LEVEL` - рівень логування
- `PRODUCTION` - прапорець production режиму
- `PUPPETEER_ALLOW_DANGEROUS` - дозвіл небезпечних Puppeteer операцій
- `PYTHONPATH` - шлях Python модулів

### Використання в Workflows

```yaml
env:
  GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
  MISTRAL_API_KEY: ${{ secrets.MISTRAL_API_KEY }}
  OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

## 📋 Чеклист перед Push

// turbo-all
```zsh
# 1. Налаштувати remote (якщо ще не зроблено)
export GITHUB_TOKEN=$(grep GITHUB_TOKEN .env | cut -d'=' -f2 | tr -d '\r\n') && \
git remote set-url origin https://$GITHUB_TOKEN@github.com/Nimda-cloud/atlastrinity.git

# 2. Перевірити якість коду
npm run lint:all

# 3. Виправити форматування
npm run format:write

# 4. Перевірити статус
git status

# 5. Додати зміни
git add .

# 6. Коміт (використовувати conventional commits)
git commit -m "type: опис"

# 7. Push
git push origin main
```

## 🎯 Conventional Commits

Формат коміт-повідомлень:
- `feat:` - нова функція
- `fix:` - виправлення бага
- `docs:` - зміни в документації
- `style:` - форматування, пробіли
- `refactor:` - рефакторинг коду
- `test:` - додавання тестів
- `chore:` - оновлення залежностей, конфігурацій

## 🚨 Усунення проблем

### Проблема: Git запитує username/password

**Рішення**:
```zsh
export GITHUB_TOKEN=$(grep GITHUB_TOKEN .env | cut -d'=' -f2 | tr -d '\r\n') && \
git remote set-url origin https://$GITHUB_TOKEN@github.com/Nimda-cloud/atlastrinity.git
```

### Проблема: Permission denied

**Перевірити**:
1. Чи правильний токен у `.env`?
2. Чи має токен необхідні права (repo, workflow)?
3. Чи не застарів токен?

### Проблема: Push rejected

**Рішення**:
```zsh
# Спершу pull з rebase
git pull --rebase origin main

# Потім push
git push origin main
```

## 📚 Корисні команди

```zsh
# Подивитись історію комітів
git log --oneline -10

# Подивитись зміни перед комітом
git diff

# Скасувати зміни у файлі
git checkout -- файл.txt

# Подивитись всі віддалені репозиторії
git remote -v

# Оновити токен у remote URL
export GITHUB_TOKEN=$(grep GITHUB_TOKEN .env | cut -d'=' -f2 | tr -d '\r\n') && \
git remote set-url origin https://$GITHUB_TOKEN@github.com/Nimda-cloud/atlastrinity.git
```

## 🎓 Для AI Агентів

**Перед будь-якою операцією з GitHub**:

1. ✅ Перевірити наявність GITHUB_TOKEN у .env
2. ✅ Налаштувати git remote з токеном
3. ✅ Виконати необхідні операції (pull/push)
4. ✅ Не виводити токен у відповідях користувачу

**При роботі з GitHub Actions**:
1. ✅ Використовувати secrets замість hardcoded значень
2. ✅ Перевіряти що workflows мають доступ до необхідних секретів
3. ✅ Тестувати локально перед push (де можливо)
