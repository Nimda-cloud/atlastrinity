#!/bin/bash

# Тестовий скрипт для перевірки Vibe стріму в Electron

echo "🧪 Тест Vibe MCP → Electron Streaming"
echo "======================================"
echo ""

# 1. Перевірка Brain
echo "1️⃣ Перевірка Brain сервера..."
if curl -s http://127.0.0.1:8000/api/health | grep -q "ok"; then
    echo "   ✅ Brain працює"
else
    echo "   ❌ Brain не працює!"
    echo "   Запустіть: npm run dev"
    exit 1
fi

# 2. Перевірка Vibe MCP сервера
echo ""
echo "2️⃣ Перевірка Vibe MCP сервера..."
if ps aux | grep 'vibe_server' | grep -v grep > /dev/null; then
    echo "   ✅ Vibe MCP сервер працює"
else
    echo "   ⚠️  Vibe MCP сервер не знайдено (запуститься при першому виклику)"
fi

# 3. Перевірка активних Vibe процесів
echo ""
echo "3️⃣ Активні Vibe процеси..."
vibe_count=$(ps aux | grep -E '/vibe -p' | grep -v grep | wc -l | tr -d ' ')
if [ "$vibe_count" -eq "0" ]; then
    echo "   ✅ Немає зависших процесів"
else
    echo "   ⚠️  Знайдено $vibe_count активних процесів:"
    ps aux | grep -E '/vibe -p' | grep -v grep | awk '{print "      PID:", $2, "Час:", $10}'
fi

# 4. Тестовий виклик через API
echo ""
echo "4️⃣ Тестовий виклик vibe_prompt..."
echo "   Відправляємо запит до Brain..."

cat > /tmp/vibe_test.json <<'EOF'
{
  "request": "Використай vibe_prompt для створення простого Python скрипта hello.py який виводить 'Hello from Vibe!'"
}
EOF

response=$(curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d @/tmp/vibe_test.json)

if echo "$response" | grep -q "success\|processing\|thinking"; then
    echo "   ✅ Запит прийнято"
    echo ""
    echo "5️⃣ Моніторинг логів..."
    echo "   Відкрийте Electron додаток і перегляньте ExecutionLog панель"
    echo "   Ви повинні побачити:"
    echo "     🚀 [VIBE-LIVE] Запуск Vibe: ..."
    echo "     🧠 [VIBE-THOUGHT] ..."
    echo "     🔧 [VIBE-ACTION] ..."
    echo "     ✅ [VIBE-LIVE] Vibe завершив роботу успішно"
    echo ""
    echo "   Альтернативно, моніторте в терміналі:"
    echo "   ./src/maintenance/monitor_vibe.sh"
else
    echo "   ❌ Помилка: $response"
    exit 1
fi

echo ""
echo "✨ Тест завершено!"
echo ""
echo "📚 Детальна інформація: docs/VIBE_STREAMING_SETUP.md"
