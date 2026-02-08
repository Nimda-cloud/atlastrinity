"""Get available GitHub Copilot models"""

import json
import os

import requests

API_KEY = os.getenv("COPILOT_API_KEY")

# Step 1: Get session token
headers = {
    "Authorization": f"token {API_KEY}",
    "Editor-Version": "vscode/1.85.0",
    "Editor-Plugin-Version": "copilot/1.144.0",
    "User-Agent": "GithubCopilot/1.144.0",
}

response = requests.get(
    "https://api.github.com/copilot_internal/v2/token",
    headers=headers,
    timeout=30,
)
response.raise_for_status()
session_token = response.json().get("token")
print(f"✓ Session token acquired: {session_token[:20]}...")

# Step 2: Get models
headers = {
    "Authorization": f"Bearer {session_token}",
    "Editor-Version": "vscode/1.85.0",
}

# Try /models endpoint
response = requests.get(
    "https://api.githubcopilot.com/models",
    headers=headers,
    timeout=30,
)

if response.status_code == 200:
    print("\n📋 Available Models:")
    models = response.json()
    print(json.dumps(models, indent=2))
else:
    print(f"\n❌ Failed to get models: {response.status_code}")
    print(f"Response: {response.text[:500]}")
