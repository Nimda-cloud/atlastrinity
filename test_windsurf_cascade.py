import os
from typing import Union, Any
from providers.windsurf import WindsurfLLM

# Configure with free model
llm = WindsurfLLM(
    model_name="deepseek-v3",
    api_key="sk-ws-01-GBW0muKg37rVCHFNsbELDH3nQh3XoscPUzngD-JBg4Y9h1JmnMoV3dKtAee78w6HL_rN_CDf6Cr2uBJjxthKBYLWPctH7g",
    max_tokens=100
)

# Test query
response = llm.invoke("Тест роботи українською. Як справи?")
print(response)
