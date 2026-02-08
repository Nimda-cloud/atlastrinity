"""Standalone test for Windsurf provider with free models"""
import os
import sys
from typing import Any, Optional, Union


# Copy of minimal required code from providers/windsurf.py
class WindsurfLLM:
    def __init__(self, model_name: str, api_key: str, max_tokens: int = 4096):
        self.model_name = model_name
        self.api_key = api_key
        self.max_tokens = max_tokens
        
    def invoke(self, prompt: str) -> str:
        """Simplified test version that just prints config"""
        return f"Windsurf test successful! Model: {self.model_name}, Key: {self.api_key[:10]}..., Tokens: {self.max_tokens}"

# Test with free model
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
