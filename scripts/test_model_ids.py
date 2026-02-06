#!/usr/bin/env python3
"""Test specific model names with Copilot"""

import os

import requests

API_KEY = os.getenv("COPILOT_API_KEY")

# Get session token
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
session_token = response.json().get("token")

# Test models
test_models = [
    "raptor-mini",
    "gpt-5-mini",
    "gpt-5.1-codex-mini",
    "o1-mini",
    "gpt-4o-mini",
]

headers = {
    "Authorization": f"Bearer {session_token}",
    "Content-Type": "application/json",
    "Editor-Version": "vscode/1.85.0",
}

for model in test_models:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "temperature": 0.1,
        "max_tokens": 10,
    }

    response = requests.post(
        "https://api.githubcopilot.com/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if response.status_code == 200:
        print(f"✅ {model}: WORKS")
    else:
        print(
            f"❌ {model}: {response.status_code} - {response.json().get('error', {}).get('message', 'Unknown error')}"
        )
