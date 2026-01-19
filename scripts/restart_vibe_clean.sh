#!/bin/bash

# Скрипт для чистого перезапуску Vibe MCP з правильним виводом в Electron

set -e

echo "🧹 Зупинка всіх процесів Vibe..."
pkill -f '/vibe -p' || true
pkill -f 'vibe_runner' || true
sleep 2

echo "🔍 Перевірка залишкових процесів..."
remaining=$(ps aux | grep -E '(vibe -p|vibe_runner)' | grep -v grep | wc -l)
if [ "$remaining" -gt 0 ]; then
    echo "⚠️  Знайдено $remaining залишкових процесів. Форсована зупинка..."
    pkill -9 -f '/vibe -p' || true
    pkill -9 -f 'vibe_runner' || true
    sleep 1
fi

echo "✅ Всі процеси Vibe зупинені"
echo ""
echo "📊 Поточний стан:"
ps aux | grep -E '(vibe_server|brain)' | grep -v grep || echo "  Немає активних процесів"
echo ""
echo "🎯 Vibe MCP готовий до роботи!"
echo ""
echo "Тепер при виклику vibe_prompt стрім буде йти в Electron через:"
echo "  1. MCP logging (ctx.log)"
echo "  2. Brain orchestrator (_log)"
echo "  3. Redis pub/sub"
echo "  4. HTTP API (/api/state)"
echo "  5. ExecutionLog компонент в UI"
