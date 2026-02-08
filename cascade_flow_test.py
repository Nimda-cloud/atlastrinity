"""Test Windsurf Cascade flow with Python 3.12"""

import os
import sys

from providers.windsurf import WindsurfLLM

# Configure with free model in cascade mode
llm = WindsurfLLM(
    model_name="deepseek-v3",
    api_key="sk-ws-01-GBW0muKg37rVCHFNsbELDH3nQh3XoscPUzngD-JBg4Y9h1JmnMoV3dKtAee78w6HL_rN_CDf6Cr2uBJjxthKBYLWPctH7g",
    max_tokens=100,
)

# Force cascade mode if needed
if hasattr(llm, "_mode"):
    llm._mode = "cascade"

print(f"Testing Windsurf in cascade mode with model: {llm.model_name}")

# Test query
try:
    response = llm.invoke(
        "Тест роботи Cascade flow українською. Опиши коротко як працює ця система."
    )
    print("\nTest successful! Response:")
    print(response)
except Exception as e:
    print(f"\nTest failed: {type(e).__name__}: {e}", file=sys.stderr)
    raise
