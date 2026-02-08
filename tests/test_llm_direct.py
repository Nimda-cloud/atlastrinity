import asyncio
import os
import sys

sys.path.append(os.getcwd())

try:
    from providers.factory import create_llm

    print("create_llm imported successfully")
except Exception as e:
    print(f"Failed to import create_llm: {e}")
    sys.exit(1)

async def test_llm():
    try:
        print("Initializing LLM via factory...")
        llm = create_llm()  # Model name should be set via configuration
        print("Invoking LLM...")
        res = await llm.ainvoke("Hi, repeat the word 'Success'")
        print(f"LLM Response: {res.content}")
    except Exception as e:
        print(f"LLM Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_llm())
