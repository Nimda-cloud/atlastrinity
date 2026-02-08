import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__)))
from src.brain.agents.atlas import Atlas


async def test_copilot():
    print("Testing Copilot Provider via Atlas Agent...")

    api_key = os.getenv("COPILOT_API_KEY") or os.getenv("GITHUB_TOKEN")
    if not api_key:
        print("ERROR: No API Key found in .env")
        return

    try:
        atlas = Atlas()
        response = await atlas.chat("Привіт, це тест зв'язку. Ти мене чуєш?")
        print(f"\nResponse received:\n{response}")
        print("\nSUCCESS: Copilot is working.")
    except Exception as e:
        print(f"\nERROR: Failed to connect to Copilot:\n{e}")
        import traceback

        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_copilot())
