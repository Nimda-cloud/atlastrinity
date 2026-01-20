import asyncio
import os
import sys

# Add project root to sys.path
sys.path.append(os.getcwd())

try:
    from providers.copilot import CopilotLLM
    print("CopilotLLM imported successfully")
except Exception as e:
    print(f"Failed to import CopilotLLM: {e}")
    sys.exit(1)

async def test_llm():
    try:
        print("Initializing CopilotLLM...")
        llm = CopilotLLM(model_name="gpt-4o")
        print("Invoking LLM...")
        res = await llm.ainvoke("Hi, repeat the word 'Success'")
        print(f"LLM Response: {res.content}")
    except Exception as e:
        print(f"LLM Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
