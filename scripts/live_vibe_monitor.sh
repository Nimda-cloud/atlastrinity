#!/bin/bash

# Live моніторинг Vibe MCP активності

echo "🔍 LIVE моніторинг Vibe MCP (Ctrl+C для виходу)"
echo "================================================"
echo ""

# Функція для показу заголовку з часом
show_header() {
    echo ""
    echo "⏰ $(date '+%H:%M:%S') - $1"
    echo "---"
}

# Показати поточний стан
show_header "Активні Vibe процеси"
ps aux | grep -E '/vibe -p' | grep -v grep | awk '{print "  PID:", $2, "CPU:", $3"%", "Cmd:", substr($0, index($0,$11))}'

echo ""
echo "📊 Починаємо live моніторинг логів..."
echo "================================================"
echo ""

# Live моніторинг з кольорами
tail -f /Users/dev/Documents/GitHub/atlastrinity/stderr.txt 2>/dev/null | while read line; do
    # Показуємо тільки важливі рядки
    if echo "$line" | grep -qE "(VIBE|vibe_prompt|ERROR|WARNING|Executing prompt|validation error)"; then
        timestamp=$(date '+%H:%M:%S')
        
        # Додаємо емодзі залежно від типу повідомлення
        if echo "$line" | grep -q "ERROR"; then
            echo "❌ [$timestamp] $line"
        elif echo "$line" | grep -q "WARNING"; then
            echo "⚠️  [$timestamp] $line"
        elif echo "$line" | grep -q "Executing prompt"; then
            echo "▶️  [$timestamp] $line"
        elif echo "$line" | grep -q "validation error"; then
            echo "🔴 [$timestamp] $line"
        else
            echo "ℹ️  [$timestamp] $line"
        fi
    fi
done
