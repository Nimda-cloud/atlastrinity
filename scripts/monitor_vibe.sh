#!/bin/bash

# Скрипт для моніторингу MCP Vibe активності

echo "=== VIBE ПРОЦЕСИ ==="
ps aux | grep -E '(vibe|vibe_server|vibe_runner)' | grep -v grep | while read line; do
    echo "$line"
done

echo ""
echo "=== ОСТАННІ ЛОГИ (stderr.txt) ==="
tail -n 50 /Users/dev/Documents/GitHub/atlastrinity/stderr.txt | grep --color=auto -E "(VIBE|vibe_prompt|ERROR|INFO|DEBUG)" || echo "Немає логів Vibe"

echo ""
echo "=== ОСТАННІ ЛОГИ (stdout.txt) ==="
tail -n 50 /Users/dev/Documents/GitHub/atlastrinity/stdout.txt | grep --color=auto -E "(VIBE|vibe_prompt|ERROR|INFO|DEBUG)" || echo "Немає логів Vibe"

echo ""
echo "=== VIBE WORKSPACE ==="
ls -lh ~/.config/atlastrinity/vibe_workspace/ 2>/dev/null || echo "Директорія не існує"

echo ""
echo "=== VIBE ІНСТРУКЦІЇ ==="
ls -lh ~/.config/atlastrinity/vibe_workspace/instructions/ 2>/dev/null || echo "Немає інструкцій"

echo ""
echo "Для реал-тайм моніторингу запустіть:"
echo "  tail -f stderr.txt | grep --line-buffered VIBE"
