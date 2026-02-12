#!/bin/bash
# Setup environment for AtlasTrinity tests
# Reads credentials from ~/.config/atlastrinity/config.yaml and sets env variables

set -e

CONFIG_FILE="$HOME/.config/atlastrinity/config.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Config not found: $CONFIG_FILE"
    exit 1
fi

echo "📋 Loading credentials from ~/.config/atlastrinity/config.yaml..."

# Extract GitHub token using grep and sed (YAML parsing)
GITHUB_TOKEN=$(grep "github_token:" "$CONFIG_FILE" 2>/dev/null | sed 's/.*github_token: //' | tr -d ' ' || echo '')

if [ -n "$GITHUB_TOKEN" ]; then
    export GITHUB_TOKEN
    echo "✅ GITHUB_TOKEN loaded (${#GITHUB_TOKEN} chars)"
else
    echo "⚠️  GITHUB_TOKEN not found in config"
fi

# Extract Copilot API key using grep and sed
COPILOT_API_KEY=$(grep "copilot_api_key:" "$CONFIG_FILE" 2>/dev/null | sed 's/.*copilot_api_key: //' | tr -d ' ' || echo '')

if [ -n "$COPILOT_API_KEY" ]; then
    export COPILOT_API_KEY
    echo "✅ COPILOT_API_KEY loaded"
else
    echo "⚠️  COPILOT_API_KEY not found in config"
fi

echo ""
# Ensure a local virtualenv exists and the minimal test deps are installed
VENV_DIR="$(pwd)/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "⚙️  Creating virtualenv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# Install full Python dependencies from requirements.txt (fallback to minimal deps)
VENV_PIP="$VENV_DIR/bin/pip"
if [ -x "$VENV_PIP" ]; then
    echo "⚙️  Installing full Python dependencies from requirements.txt..."
    "$VENV_PIP" install --upgrade pip setuptools wheel
    REQS_FILE="$(pwd)/requirements.txt"
    if [ -f "$REQS_FILE" ]; then
        echo "⚙️  Found requirements.txt, installing..."
        "$VENV_PIP" install -r "$REQS_FILE"
    else
        echo "⚠️  requirements.txt not found, installing minimal test dependency: python-dotenv"
        "$VENV_PIP" install python-dotenv>=1.0.0
    fi
else
    echo "⚠️  Could not find pip at $VENV_PIP - please ensure your Python venv is functional"
fi

# Install NPM dependencies for full environment if npm is available
if command -v npm >/dev/null 2>&1; then
    echo "⚙️  Installing NPM dependencies..."
    npm install >/dev/null 2>&1 || echo "⚠️ npm install failed; please run 'npm install' manually"
else
    echo "⚠️  npm not found; skip NPM dependencies. Install node/npm to enable frontend features"
fi

echo "✨ Full environment ready for testing and development"
echo "Run tests with: ./.venv/bin/pytest tests/"
