#!/bin/bash

# Fresh Install Test Script
# Видаляє ВСЕ та симулює нову установку

set -e  # Exit on error

echo "🧹 =========================================="
echo "   FRESH INSTALL SIMULATION"
echo "   Це видалить ВСІ локальні налаштування!"
echo "=========================================="
echo ""

# Function to display MCP servers table
show_mcp_servers_table() {
    echo ""
    echo "🔧 MCP СЕРВЕРИ - СТАТУС І ДОСТУПНІСТЬ:"
    echo "┌─────────────────────┬─────────────┬─────────────────┬────────────┐"
    printf "│ %-19s │ %-11s │ %-15s │ %-10s │\n" "СЕРВЕР" "ІНСТРУМЕНТІВ" "СТАТУС" "ТИР"
    echo "├─────────────────────┼─────────────┼─────────────────┼────────────┤"

    # Check if config exists
    CONFIG_FILE="$PROJECT_ROOT/config/mcp_servers.json.template"
    if [ ! -f "$CONFIG_FILE" ]; then
        printf "│ %-19s │ %-11s │ %-15s │ %-10s │\n" "КОНФІГ НЕ ЗНАЙДЕНО" "N/A" "❌" "N/A"
        echo "└─────────────────────┴─────────────┴─────────────────┴────────────┘"
        return
    fi

    # Parse MCP config and display servers
    python3 -c "
import json
import re
import os

# Load config
config_file = '$CONFIG_FILE'
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)

servers = config.get('mcpServers', {})
total_servers = 0
enabled_servers = 0

for server_name, server_config in servers.items():
    if server_name.startswith('_'):
        continue
    
    total_servers += 1
    
    # Extract tool count from description - improved regex
    description = server_config.get('description', '')
    # Match patterns like: (63 tools), (168+ tools), (8 tools)
    tool_match = re.search(r'\\((\\d+)(?:\\+)?\\s*(?:tools?|інструментів?)\\)', description)
    tool_count = tool_match.group(1) if tool_match else 'N/A'
    
    # Check status
    disabled = server_config.get('disabled', False)
    tier = server_config.get('tier', 'N/A')
    
    if disabled:
        status = 'Вимкнено'
        status_icon = '⭕'
    else:
        enabled_servers += 1
        status = 'Доступний'
        status_icon = '✅'
    
    # Format server name (truncate if too long)
    display_name = server_name[:18] if len(server_name) > 18 else server_name
    
    print(f'│ {display_name:<18} │ {str(tool_count):>11} │ {status_icon} {status:<11} │ {str(tier):>10} │')

print('└─────────────────────┴─────────────┴─────────────────┴────────────┘')
print(f'Загалом серверів: {total_servers} | Активних: {enabled_servers} | Вимкнених: {total_servers - enabled_servers}')
    "
}

INTERACTIVE=true
for arg in "$@"; do
    if [[ "$arg" == "-y" || "$arg" == "--yes" ]]; then
        INTERACTIVE=false
    fi
done

# Ensure paths are set
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Check for active virtual environment
if [[ -n "$VIRTUAL_ENV" && "$INTERACTIVE" == "true" ]]; then
    echo "⚠️  You are currently in an ACTIVATED virtual environment: $VIRTUAL_ENV"
    echo "   Starting a fresh install from an active environment can cause issues."
    echo "   Please run 'deactivate' first, then try again."
    echo ""
    if ! confirm "Do you want to continue anyway?" "N"; then
        echo "❌ Aborted. Please deactivate and restart."
        exit 1
    fi
fi

# Confirm function
confirm() {
    local msg=$1
    local default=$2
    
    if [[ "$INTERACTIVE" == "false" ]]; then
        return 0
    fi

    if [[ "$default" == "Y" ]]; then
        read -t 5 -p "❓ $msg (Y/n): " choice </dev/tty || choice="Y"
    else
        read -t 5 -p "❓ $msg (y/N): " choice </dev/tty || choice="N"
    fi
    echo ""
    if [[ "$choice" =~ ^[Yy]$ || ( -z "$choice" && "$default" == "Y" ) ]]; then
        return 0
    else
        return 1
    fi
}

# Check for active virtual environment
if [[ -n "$VIRTUAL_ENV" && "$INTERACTIVE" == "true" ]]; then
    echo "⚠️  You are currently in an ACTIVATED virtual environment: $VIRTUAL_ENV"
    echo "   Starting a fresh install from an active environment can cause issues."
    echo "   Please run 'deactivate' first, then try again."
    echo ""
    if ! confirm "Do you want to continue anyway?" "N"; then
        echo "❌ Aborted. Please deactivate and restart."
        exit 1
    fi
fi


# Ensure Brew and basic paths are available
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew NOT found. Please install it first."
    exit 1
fi

if ! confirm "This will DELETE ALL local configuration and environments. Continue?" "Y"; then
    echo "❌ Cancelled"
    exit 1
fi
# 0. Backup Prompt
echo "🛡️  Backup Check"
if confirm "Create database backup before wiping?" "Y"; then
    echo "📦 Backing up databases..."
    # Use venv python if available (venv hasn't been deleted yet), otherwise python3.12/python3
    if [ -x ".venv/bin/python" ]; then
        BACKUP_PYTHON=".venv/bin/python"
    elif command -v python3.12 &> /dev/null; then
        BACKUP_PYTHON="python3.12"
    else
        BACKUP_PYTHON="python3"
    fi
    $BACKUP_PYTHON src/maintenance/setup_dev.py --backup
    if [ $? -eq 0 ]; then
        echo "✅ Backup completed successfully."
    else
        echo "❌ Backup failed! Aborting to prevent data loss."
        exit 1
    fi
else
    echo "⚠️  Skipping backup. Hope you know what you are doing!"
fi

echo ""
echo "📦 Крок 1/8: Видалення Python venv..."
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
echo "📦 Крок 5/8: Видалення Swift компіляції та XcodeBuildMCP..."
if [ -d "vendor/mcp-server-macos-use/.build" ]; then
    rm -rf vendor/mcp-server-macos-use/.build
    echo "✅ Swift .build видалено (macos-use)"
fi

if [ -d "vendor/mcp-server-googlemaps/.build" ]; then
    rm -rf vendor/mcp-server-googlemaps/.build
    echo "✅ Swift .build видалено (googlemaps)"
fi

echo "ℹ️  XcodeBuildMCP тепер є частиною репозиторію в vendor/ (не потребує окремого клонування)"

echo ""
echo "📦 Крок 6/8: Видалення глобальної конфігурації..."

DELETE_MODELS="n"
if [ -d "$HOME/.config/atlastrinity/models" ]; then
    echo ""
    echo "❓ Бажаєте видалити AI моделі (TTS/STT)? (Заощадить ~3GB трафіку якщо залишити)"
    if confirm "Видалити моделі?" "N"; then
        DELETE_MODELS="y"
        echo "   -> Моделі буде видалено."
    else
        DELETE_MODELS="n"
        echo "   -> Моделі буде збережено."
    fi
fi

if [ -d "$HOME/.config/atlastrinity" ]; then
    if [ "$DELETE_MODELS" == "n" ] && [ -d "$HOME/.config/atlastrinity/models" ]; then
        # Preserve models and memory structure, but clean ChromaDB
        echo "   -> Збереження моделей, очищення ChromaDB..."
        TEMP_MODELS="/tmp/atlastrinity_models_backup"
        rm -rf "$TEMP_MODELS"
        mv "$HOME/.config/atlastrinity/models" "$TEMP_MODELS"
        
        # Clean ChromaDB specifically before removing the whole config
        rm -rf "$HOME/.config/atlastrinity/memory/chroma" 2>/dev/null || true
        rm -rf "$HOME/.config/atlastrinity/data/golden_fund" 2>/dev/null || true
        
        rm -rf "$HOME/.config/atlastrinity"
        
        # Recreate and restore
        mkdir -p "$HOME/.config/atlastrinity"
        mkdir -p "$HOME/.config/atlastrinity/memory"
        mv "$TEMP_MODELS" "$HOME/.config/atlastrinity/models"
        echo "✅ ~/.config/atlastrinity видалено (Models збережено, ChromaDB очищено)"
    else
        # Full deletion including ChromaDB
        rm -rf "$HOME/.config/atlastrinity"
        # Also cleanup the often-auto-created stanza_resources in Home if it exists
        rm -rf "$HOME/stanza_resources"
        echo "✅ ~/.config/atlastrinity видалено (Models теж видалено)"
        echo "✅ ~/stanza_resources видалено"
    fi
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
echo "  1️⃣  python3.12 src/maintenance/setup_dev.py  (або просто python3)"
echo "  2️⃣  npm run dev"
echo ""

if confirm "Бажаєте запустити налаштування (setup_dev.py) прямо зараз?" "Y"; then
    # Pass --yes if we are in non-interactive mode
    SETUP_ARGS=""
    if [[ "$INTERACTIVE" == "false" ]]; then
        SETUP_ARGS="--yes"
    fi

    # Try python3.12 first, then python3, then python
    PYTHON_CMD="python3" # Default to python3
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Error: No python interpreter found (python3.12, python3, or python)."
        exit 1
    fi
    
    echo "🚀 Запуск $PYTHON_CMD src/maintenance/setup_dev.py $SETUP_ARGS..."
    $PYTHON_CMD src/maintenance/setup_dev.py $SETUP_ARGS

    # Sync secrets to GitHub if possible
    echo ""
    echo "🔗 Перевірка можливості синхронізації секретів з GitHub..."
    if [ -f "scripts/sync_secrets.sh" ]; then
        bash "scripts/sync_secrets.sh"
    else
        echo "⚠️ scripts/sync_secrets.sh не знайдено, пропускаємо синхронізацію."
    fi
else
    echo "👋 Ви можете запустити налаштування пізніше."
fi

echo ""
echo "Очікуваний результат:"
echo "  ✅ Відновлення баз даних з backups/"
echo "  ✅ Створення .venv"
echo "  ✅ Встановлення Python пакетів (включаючи pandas, numpy, matplotlib)"
echo "  ✅ Встановлення NPM пакетів"
echo "  ✅ Компіляція нативних MCP серверів:"
echo "     - macos-use (40+ інструментів для macOS)"
echo "     - googlemaps (Google Maps API з фільтрами)"
echo "     - XcodeBuildMCP (Xcode automation для iOS/macOS)"
echo "  ✅ Завантаження моделей (Whisper, TTS)"
echo "  ⚠️  Ініціалізація баз даних (відбудеться при першому запуску)"
echo "  ⚠️  Налаштування Golden Fund Knowledge Base (відбудеться при першому запуску)"
echo "  ✅ Інтеграція MCP серверів"
echo ""

# Show MCP servers table
show_mcp_servers_table
