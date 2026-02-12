#!/bin/bash
# AtlasTrinity Full Cleanup Script
# Очищає проект до стану fresh git clone
# 
# Використання: ./scripts/clean_full.sh

set -e

echo "╔══════════════════════════════════════════╗"
echo "║  AtlasTrinity Full Cleanup               ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Визначаємо корінь проекту
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# === Python Environment ===
echo "🐍 Очищення Python середовища..."
if [ -d ".venv" ]; then
    rm -rf .venv
    echo "  ✓ Видалено .venv/"
fi

if [ -d "dist_venv" ]; then
    rm -rf dist_venv
    echo "  ✓ Видалено dist_venv/"
fi

# Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name ".eggs" -exec rm -rf {} + 2>/dev/null || true
echo "  ✓ Очищено Python cache"

# === Node.js Environment ===
echo ""
echo "📦 Очищення Node.js середовища..."
if [ -d "node_modules" ]; then
    rm -rf node_modules
    echo "  ✓ Видалено node_modules/"
fi

# Vite cache
if [ -d ".vite" ]; then
    rm -rf .vite
    echo "  ✓ Видалено .vite/"
fi

# === Build Artifacts ===
echo ""
echo "🔨 Очищення build артефактів..."
if [ -d "dist" ]; then
    rm -rf dist
    echo "  ✓ Видалено dist/"
fi

if [ -d "release" ]; then
    rm -rf release
    echo "  ✓ Видалено release/"
fi

# TypeScript build info
rm -f tsconfig.tsbuildinfo tsconfig.main.tsbuildinfo 2>/dev/null || true
echo "  ✓ Видалено *.tsbuildinfo"

# === Swift MCP Build ===
echo ""
echo "🦅 Очищення Swift build..."
if [ -d "vendor/mcp-server-macos-use/.build" ]; then
    rm -rf vendor/mcp-server-macos-use/.build
    echo "  ✓ Видалено Swift .build/"
fi
if [ -d "vendor/mcp-server-macos-use/.swiftpm" ]; then
    rm -rf vendor/mcp-server-macos-use/.swiftpm
    echo "  ✓ Видалено Swift .swiftpm/"
fi

# === Logs ===
echo ""
echo "📜 Очищення логів..."
if [ -d "logs" ]; then
    rm -rf logs/*
    echo "  ✓ Очищено logs/"
fi

# === macOS junk ===
echo ""
echo "🍎 Очищення macOS файлів..."
find . -name ".DS_Store" -delete 2>/dev/null || true
echo "  ✓ Видалено .DS_Store файли"

# === Local .env (not .env.example) ===
if [ -f ".env" ]; then
    echo ""
    echo "⚠️  Знайдено .env файл. Він НЕ видаляється (містить ваши ключі)."
    echo "   Якщо хочете повністю очистити, видаліть вручну: rm .env"
fi

# === Summary ===
echo ""
echo "════════════════════════════════════════════"
echo "✅ Проект очищено до git clone стану!"
echo ""
echo "Наступний крок:"
echo "  python3 scripts/setup_dev.py"
echo "════════════════════════════════════════════"
