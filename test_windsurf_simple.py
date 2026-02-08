#!/usr/bin/env python3
"""
Simple test for Windsurf Cascade mode.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for Windsurf
os.environ["WINDSURF_API_KEY"] = "sk-ws-01-GBW0muKg37rVCHFNsbELDH3nQh3XoscPUzngD-JBg4Y9h1JmnMoV3dKtAee78w6HL_rN_CDf6Cr2uBJjxthKBYLWPctH7g"
os.environ["WINDSURF_LS_PORT"] = "54336"
os.environ["WINDSURF_LS_CSRF"] = "da9755d1-18ce-4087-b94c-3cc4e6b67f08"
os.environ["WINDSURF_MODEL"] = "deepseek-v3"  # Free model

try:
    from providers.windsurf import WindsurfLLM

    print("Testing Windsurf provider with free model...")

    # Force cascade mode
    os.environ["WINDSURF_MODE"] = "cascade"

    llm = WindsurfLLM()
    print(f"Initialized with mode: {llm._mode}, model: {llm.model_name}")

    # Simple test message
    from langchain_core.messages import HumanMessage, SystemMessage

    messages = [
        SystemMessage(content="You are helpful. Answer briefly."),
        HumanMessage(content="Hello, what is 2+2?")
    ]

    print("Sending test message...")
    result = llm.invoke(messages)
    print(f"Response: {result.content}")

    print("✓ Windsurf provider works!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
