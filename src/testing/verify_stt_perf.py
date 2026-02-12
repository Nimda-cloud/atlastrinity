import asyncio
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.voice.stt import WhisperSTT


async def main():
    stt = WhisperSTT()

    # Path to a test wav file if exists, or just check initialization
    time.time()
    await stt.get_model()


if __name__ == "__main__":
    asyncio.run(main())
