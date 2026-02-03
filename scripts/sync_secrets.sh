#!/bin/bash
# scripts/sync_secrets.sh
# Synchronizes secrets from local .env to GitHub repository secrets using 'gh' CLI.

set -e

ENV_FILE="$HOME/.config/atlastrinity/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Local .env file not found at $ENV_FILE"
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) not found. Please install it with: brew install gh"
    exit 1
fi

# Load GITHUB_TOKEN from .env and export as GH_TOKEN for the CLI
GH_TOKEN_VAL=$(grep "^GITHUB_TOKEN=" "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | sed "s/^['\"]//;s/['\"]$//")
if [ -n "$GH_TOKEN_VAL" ]; then
    export GH_TOKEN="$GH_TOKEN_VAL"
    echo "🔑 Using GITHUB_TOKEN from .env for authentication."
fi

# Check if authenticated (via GH_TOKEN or existing session)
if ! gh auth status &> /dev/null; then
    echo "❌ Authentication failed. Ensure GITHUB_TOKEN in .env is valid or run: gh auth login"
    exit 1
fi

echo "🎬 Starting secrets synchronization for $(basename $(pwd))..."

# List of secrets to sync
SECRETS_TO_SYNC=(
    "MISTRAL_API_KEY"
    "COPILOT_API_KEY"
    "GOOGLE_MAPS_API_KEY"
    "OPENAI_API_KEY"
    "ANTHROPIC_API_KEY"
    "SONAR_TOKEN"
)

SYNC_COUNT=0

for SECRET in "${SECRETS_TO_SYNC[@]}"; do
    # Extract value from .env, excluding comments and handling simple Key=Value pairs
    VALUE=$(grep "^$SECRET=" "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | sed "s/^['\"]//;s/['\"]$//")
    
    if [ -n "$VALUE" ]; then
        echo "📤 Syncing $SECRET..."
        echo "$VALUE" | gh secret set "$SECRET"
        SYNC_COUNT=$((SYNC_COUNT + 1))
    else
        echo "ℹ️  Skipping $SECRET (not found in .env)"
    fi
done

echo ""
echo "✅ Successfully synced $SYNC_COUNT secrets to GitHub repository."
echo "💡 You can now run your CI/CD pipelines with full access to these keys."
