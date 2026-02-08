import os
import sys
from typing import Any, Union

# Minimal imports to avoid dependencies
from providers.windsurf import WindsurfLLM

# Configure with free model
llm = WindsurfLLM(
    model_name="deepseek-v3",
    api_key="sk-ws-01-GBW0muKg37rVCHFNsbELDH3nQh3XoscPUzngD-JBg4Y9h1JmnMoV3dKtAee78w6HL_rN_CDf6Cr2uBJjxthKBYLWPctH7g",
    max_tokens=100
)

# Test query
try:
    response = llm.invoke("Тест роботи українською. Як справи?")
    print("Test successful! Response:")
    print(response)
except Exception as e:
    print(f"Test failed: {type(e).__name__}: {e}", file=sys.stderr)
    raise
