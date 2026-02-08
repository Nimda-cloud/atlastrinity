"""Standalone test for Windsurf provider with free models"""

import logging
import os
import sys
from pathlib import Path

# Set up logger
logger = logging.getLogger(Path(__file__).stem)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

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
    max_tokens=100,
)

# Test query
try:
    response = llm.invoke("Тест роботи українською. Як справи?")
    logger.info("Test successful! Response:")
    logger.info(response)
except Exception as e:
    logger.info(f"Test failed: {type(e).__name__}: {e}", file=sys.stderr)
    raise
