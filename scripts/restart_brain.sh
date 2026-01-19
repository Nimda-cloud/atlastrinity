#!/bin/bash

# Швидкий перезапуск Brain після виправлень

echo "🔄 Перезапуск Brain після виправлень..."
echo "======================================"
echo ""

echo "1️⃣ Пошук процесу Brain..."
brain_pid=$(ps aux | grep 'brain.server' | grep -v grep | awk '{print $2}')

if [ -n "$brain_pid" ]; then
    echo "   ⚠️  Brain працює (PID: $brain_pid)"
    echo "   🛑 Зупинка..."
    kill $brain_pid
    sleep 2
    
    # Перевірка чи зупинився
    if ps -p $brain_pid > /dev/null 2>&1; then
        echo "   ⚠️  Форсована зупинка..."
        kill -9 $brain_pid
        sleep 1
    fi
    echo "   ✅ Brain зупинений"
else
    echo "   ℹ️  Brain не запущений"
fi

echo ""
echo "2️⃣ Перевірка виправлень..."

# Перевірка step_id
if grep -q "step_id = step.get" src/brain/agents/tetyana.py; then
    echo "   ✅ step_id визначений рано"
else
    echo "   ❌ step_id не виправлено"
fi

# Перевірка err_str  
if grep -q "err_str = str(last_error)" src/brain/orchestrator.py; then
    echo "   ✅ err_str правильно визначений"
else
    echo "   ❌ err_str не виправлено"
fi

# Перевірка _format_mcp_result
if grep -q "_format_mcp_result(v_res_raw)" src/brain/agents/tetyana.py; then
    echo "   ✅ CallToolResult конвертація правильна"
else
    echo "   ❌ Конвертація не виправлена"
fi

echo ""
echo "3️⃣ Запуск Brain..."
echo "   Виконайте в терміналі де запущений npm run dev:"
echo "   Ctrl+C (якщо потрібно)"
echo "   npm run dev"
echo ""
echo "   Або якщо npm run dev вже працює, виправлення"
echo "   застосуються автоматично при наступному запиті."
echo ""
echo "✅ Готово! Brain готовий до роботи після перезапуску."
