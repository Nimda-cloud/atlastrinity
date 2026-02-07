#!/bin/bash

# Скрипт для повного очищення кешу перед запуском dev режиму

echo "🧹 Очищення всіх кешів..."

# Очищення Python кешу
echo "  • Очищення Python __pycache__..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null

# Очищення Linter та Test кешів
echo "  • Очищення linter та test кешів (.ruff, .pytest, .pyrefly)..."
rm -rf .ruff_cache .pytest_cache .pyrefly_cache .mypy_cache 2>/dev/null

# Очищення Node кешу
echo "  • Очищення Node node_modules/.cache..."
rm -rf node_modules/.cache 2>/dev/null

# Очищення Vite кешу
echo "  • Очищення Vite кешу..."
rm -rf .vite 2>/dev/null

# Очищення логів
echo "  • Очищення логів..."
rm -rf logs/* 2>/dev/null

# Очищення Electron cache
echo "  • Очищення Electron кешу..."
rm -rf ~/Library/Caches/atlastrinity* 2>/dev/null

# Очищення локального кешу в .config
echo "  • Очищення локального кешу конфігурації..."
rm -rf ~/.config/atlastrinity/cache/* 2>/dev/null

# Очищення Redis (ВИБІРКОВЕ - зберігаємо сесії!)
echo "  • Очищення Redis (cache only, preserving sessions)..."
# Видаляємо тільки кеш-ключі, зберігаючи сесії та історію завдань
redis-cli KEYS "cache:*" 2>/dev/null | xargs -r redis-cli DEL 2>/dev/null || true
redis-cli KEYS "temp:*" 2>/dev/null | xargs -r redis-cli DEL 2>/dev/null || true
redis-cli KEYS "lock:*" 2>/dev/null | xargs -r redis-cli DEL 2>/dev/null || true
# НЕ видаляємо: session:*, task:*, tasks:*, history:*, state:*
echo "    (Sessions preserved)"

# Очищення білдів
echo "  • Очищення дистрибутивів та білд-інфо..."
rm -rf dist 2>/dev/null
rm -rf release 2>/dev/null
rm -f *.tsbuildinfo 2>/dev/null

# Очищення зображень STT/TTT

# Вбивство завислих процесів
echo "  • Вбивство завислих процесів (port 8000, 8085, 8088, MCP servers)..."
# Вбиваємо все на портах 8000/8085/8088 (brain.server, universal_proxy)
lsof -ti :8000 -ti :8085 -ti :8088 | xargs kill -9 2>/dev/null || true
# Вбиваємо основні MCP сервери за маскою
pkill -9 -f vibe_server 2>/dev/null || true
pkill -9 -f universal_proxy.py 2>/dev/null || true
pkill -9 -f memory_server 2>/dev/null || true
pkill -9 -f graph_server 2>/dev/null || true
pkill -9 -f mcp-server 2>/dev/null || true
pkill -9 -f macos-use 2>/dev/null || true
pkill -9 -f brain.server 2>/dev/null || true

# Вбиваємо процеси на портах Vite/Vibe/Proxies (3000, 3001, 8080, 8090)
echo "  • Звільнення портів UI/Dev (3000, 3001, 8080, 8090)..."
lsof -ti :3000 | xargs kill -9 2>/dev/null || true
lsof -ti :3001 | xargs kill -9 2>/dev/null || true
lsof -ti :8080 | xargs kill -9 2>/dev/null || true
lsof -ti :8090 | xargs kill -9 2>/dev/null || true


echo "✅ Кеші очищені!"
