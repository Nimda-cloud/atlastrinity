import logging
import os
import sys
from pathlib import Path
from typing import Any, Union

from providers.windsurf import WindsurfLLM

logger = logging.getLogger(Path(__file__).stem)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
# Set up logger
logger = logging.getLogger(Path(__file__).stem)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
# Configure with free model
llm = WindsurfLLM(
    model_name="deepseek-v3",
    api_key="sk-ws-01-GBW0muKg37rVCHFNsbELDH3nQh3XoscPUzngD-JBg4Y9h1JmnMoV3dKtAee78w6HL_rN_CDf6Cr2uBJjxthKBYLWPctH7g",
    max_tokens=100,
)
# Test query
response = llm.invoke("Тест роботи українською. Як справи?")
logger.info(response)
