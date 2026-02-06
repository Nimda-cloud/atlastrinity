#!/usr/bin/env python3
"""Direct API test for native model support"""

import json
import os
import sys

import requests

# Get session token
print("🔑 Fetching token...")
API_KEY = os.getenv("COPILOT_API_KEY")
headers = {
    "Authorization": f"token {API_KEY}",
    "Editor-Version": "vscode/1.85.0",
    "Editor-Plugin-Version": "copilot/1.144.0",
    "User-Agent": "GithubCopilot/1.144.0",
}
resp = requests.get("https://api.github.com/copilot_internal/v2/token", headers=headers)
if resp.status_code != 200:
    print(f"❌ Failed to get token: {resp.text}")
    sys.exit(1)

token = resp.json().get("token")
print("✅ Token acquired")

# Models to test natively
models_to_test = ["gpt-4o", "oswe-vscode-secondary", "gpt-5-mini", "grok-code-fast-1", "gpt-4.1"]

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "Editor-Version": "vscode/1.85.0",
}

print("\n🧪 TESTING NATIVE CONNECTIVITY (NO PROXY, NO TRANSLATION):")
print("=" * 60)

for model in models_to_test:
    print(f"\n📡 Requesting Native Model: '{model}'")
    payload = {"model": model, "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 10}

    try:
        r = requests.post(
            "https://api.githubcopilot.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=15,
        )

        if r.status_code == 200:
            print(f"✅ SUCCESS! Model '{model}' exists natively.")
            print(f"   Response: {json.dumps(r.json())[:100]}...")
        else:
            print(f"❌ FAILED. Model '{model}' REJECTED by GitHub.")
            print(f"   Status: {r.status_code}")
            print(f"   Error: {r.text}")

    except Exception as e:
        print(f"❌ Exception: {e}")

print("\n" + "=" * 60)
