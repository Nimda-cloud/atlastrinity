"""Compare reasoning models from GitHub Copilot API"""

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

# Get models
headers = {
    "Authorization": f"Bearer {session_token}",
    "Editor-Version": "vscode/1.85.0",
}
response = requests.get(
    "https://api.githubcopilot.com/models",
    headers=headers,
    timeout=30,
)

models_data = response.json()

# Filter reasoning/code models

reasoning_keywords = ["gpt-4", "gpt-5", "codex", "grok", "o1", "o3"]
reasoning_models = []

for model in models_data.get("data", []):
    model_id = model.get("id", "")
    model_name = model.get("name", "")
    family = model.get("capabilities", {}).get("family", "")

    # Check if it's a reasoning/code model
    if any(kw in model_id.lower() or kw in family.lower() for kw in reasoning_keywords):
        caps = model.get("capabilities", {})
        limits = caps.get("limits", {})
        supports = caps.get("supports", {})

        reasoning_models.append(
            {
                "id": model_id,
                "name": model_name,
                "family": family,
                "max_tokens": limits.get("max_output_tokens", "N/A"),
                "context": limits.get("max_context_window_tokens", "N/A"),
                "tool_calls": supports.get("tool_calls", False),
                "structured_outputs": supports.get("structured_outputs", False),
                "model_picker_enabled": model.get("model_picker_enabled", False),
            }
        )

# Sort by family and print
reasoning_models.sort(key=lambda x: (x["family"], x["id"]))

for m in reasoning_models:
    emoji = "✅" if m["model_picker_enabled"] else "  "
