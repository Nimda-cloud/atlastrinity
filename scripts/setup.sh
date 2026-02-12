#!/bin/bash
# AtlasTrinity Development Setup Script
# Quick setup wrapper for setup_dev.py

set -e  # Exit on error

echo "╔══════════════════════════════════════════╗"
echo "║  AtlasTrinity Development Setup         ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.8+ and try again."
    exit 1
fi

# Run the Python setup script
pushd "$(dirname "$0")/.." >/dev/null
export PYTHONPATH="$(pwd)"
python3 "src/maintenance/setup_dev.py"

# Sync secrets to GitHub if possible
echo ""
echo "🔗 Перевірка можливості синхронізації секретів з GitHub..."
if [ -f "scripts/sync_secrets.sh" ]; then
    bash "scripts/sync_secrets.sh"
else
    echo "⚠️ scripts/sync_secrets.sh не знайдено, пропускаємо синхронізацію."
fi

popd >/dev/null

echo ""
echo "============================================================"
echo "✓ Setup complete! 🎉"
echo ""
echo "Наступні кроки:"
echo "  1. Додайте API ключі в ~/.config/atlastrinity/.env"
echo "     - COPILOT_API_KEY (обов'язково)"
echo "     - GITHUB_TOKEN (опціонально)"
echo "  2. Запустіть систему: npm run dev"
echo ""
echo "Інформація:"
echo "  • Конфіги: ~/.config/atlastrinity/"
echo "  • TTS моделі: ~/.config/atlastrinity/models/tts/"
echo "  • STT моделі: ~/.config/atlastrinity/models/faster-whisper/"
echo "  • Логи: ~/.config/atlastrinity/logs/"
echo ""
