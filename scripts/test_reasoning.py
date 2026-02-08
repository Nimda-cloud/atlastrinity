"""Test codex models with actual reasoning task"""

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

# Test models with reasoning task
test_models = [
    "gpt-5.1-codex-mini",
    "gpt-5-codex",
    "gpt-5.1-codex",
    "gpt-5-mini",
    "gpt-4.1",
]

headers = {
    "Authorization": f"Bearer {session_token}",
    "Content-Type": "application/json",
    "Editor-Version": "vscode/1.85.0",
}

reasoning_prompt = "Calculate 15 * 23 and explain your reasoning step by step."

print("🧪 Testing Reasoning Models:")
print("=" * 80)

for model in test_models:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful reasoning assistant."},
            {"role": "user", "content": reasoning_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 500,
    }

    try:
        response = requests.post(
            "https://api.githubcopilot.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )

        if response.status_code == 200:
            data = response.json()
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"\n✅ {model}")
            print(f"   Response: {answer[:150]}...")
        else:
            error_msg = response.json().get("error", {}).get("message", "Unknown error")
            print(f"\n❌ {model}")
            print(f"   Error ({response.status_code}): {error_msg}")
    except Exception as e:
        print(f"\n❌ {model}")
        print(f"   Exception: {str(e)[:100]}")

print("\n" + "=" * 80)
