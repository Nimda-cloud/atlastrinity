#!/bin/bash

# Скрипт для перевірки виправлень помилок

echo "🔍 Перевірка виправлених помилок"
echo "================================="
echo ""

echo "1️⃣ Перевірка err_str → last_error..."
if grep -q "err_str = str(last_error)" src/brain/orchestrator.py; then
    echo "   ✅ err_str правильно визначений"
else
    echo "   ❌ err_str не знайдено"
fi

echo ""
echo "2️⃣ Перевірка CallToolResult → _format_mcp_result..."
if grep -q "_format_mcp_result(v_res_raw)" src/brain/agents/tetyana.py; then
    echo "   ✅ CallToolResult конвертується правильно"
else
    echo "   ❌ Конвертація не знайдена"
fi

echo ""
echo "3️⃣ Перевірка наявності _format_mcp_result методу..."
if grep -q "def _format_mcp_result" src/brain/agents/tetyana.py; then
    echo "   ✅ Метод _format_mcp_result існує"
else
    echo "   ❌ Метод не знайдено"
fi

echo ""
echo "✨ Виправлені помилки:"
echo "   - NameError: name 'prompt' is not defined → вже було в vibe_server.py"
echo "   - NameError: name 'err_str' is not defined → err_str = str(last_error)"
echo "   - AttributeError: 'CallToolResult' object has no attribute 'get' → _format_mcp_result()"
echo ""
echo "📚 Детальний звіт: docs/VIBE_STREAMING_SETUP.md"
