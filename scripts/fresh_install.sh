#!/bin/bash

# Fresh Install Test Script
# Видаляє ВСЕ та симулює нову установку

set -e  # Exit on error

echo "🧹 =========================================="
echo "   FRESH INSTALL SIMULATION"
echo "   Це видалить ВСІ локальні налаштування!"
echo "=========================================="
echo ""

# Confirm
read -p "⚠️  Продовжити? Це видалить .venv, node_modules, ~/.config/atlastrinity (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Скасовано"
    exit 1
fi

echo ""
echo "📦 Крок 1/6: Видалення Python venv..."
if [ -d ".venv" ]; then
    rm -rf .venv
    echo "✅ .venv видалено"
else
    echo "ℹ️  .venv не існує"
fi

echo ""
echo "📦 Крок 2/8: Видалення node_modules + lockfile..."
if [ -d "node_modules" ]; then
    rm -rf node_modules
    echo "✅ node_modules видалено"
else
    echo "ℹ️  node_modules не існує"
fi

if [ -f "package-lock.json" ]; then
    rm -f package-lock.json
    echo "✅ package-lock.json видалено"
else
    echo "ℹ️  package-lock.json не існує"
fi

echo ""
echo "📦 Крок 3/8: Видалення Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
echo "✅ Python cache видалено"

echo ""
echo "📦 Крок 4/8: Видалення build артефактів..."
rm -rf dist/ release/ dist_venv/ .vite/
echo "✅ Build artifacts видалено"

echo ""
echo "📦 Крок 5/8: Видалення Swift компіляції..."
if [ -d "vendor/mcp-server-macos-use/.build" ]; then
    rm -rf vendor/mcp-server-macos-use/.build
    echo "✅ Swift .build видалено"
else
    echo "ℹ️  Swift .build не існує"
fi

echo ""
echo "📦 Крок 6/8: Видалення глобальної конфігурації..."
if [ -d "$HOME/.config/atlastrinity" ]; then
    rm -rf "$HOME/.config/atlastrinity"
    echo "✅ ~/.config/atlastrinity видалено"
else
    echo "ℹ️  ~/.config/atlastrinity не існує"
fi

echo ""
echo "📦 Крок 7/8: Видалення Electron cache..."
if [ -d "$HOME/Library/Application Support/atlastrinity" ]; then
    rm -rf "$HOME/Library/Application Support/atlastrinity"
    echo "✅ Electron userData видалено"
else
    echo "ℹ️  Electron userData не існує"
fi

echo ""
echo "📦 Крок 8/8: Очищення логів та кешів..."
rm -f brain_start.log *.log
find . -name ".DS_Store" -delete 2>/dev/null || true
echo "✅ Логи та .DS_Store видалено"

echo ""
echo "🎉 =========================================="
echo "   ОЧИЩЕННЯ ЗАВЕРШЕНО!"
echo "=========================================="
echo ""
echo "Тепер запустіть:"
echo "  1️⃣  python scripts/setup_dev.py"
echo "  2️⃣  npm run dev"
echo ""
echo "Очікуваний результат:"
echo "  ✅ Відновлення баз даних з backups/"
echo "  ✅ Створення .venv"
echo "  ✅ Встановлення Python пакетів"
echo "  ✅ Встановлення NPM пакетів"
echo "  ✅ Компіляція Swift macos-use"
echo "  ✅ Завантаження моделей (Whisper, TTS)"
echo "  ✅ Ініціалізація баз даних"
echo ""
