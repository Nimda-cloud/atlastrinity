import asyncio
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.voice.stt import WhisperSTT


async def main():
    stt = WhisperSTT()
    print(f"Testing Whisper STT with model: {stt.model_name} on {stt.device}")

    # Path to a test wav file if exists, or just check initialization
    print("Loading model...")
    start = time.time()
    await stt.get_model()
    print(f"Model loaded in {time.time() - start:.2f}s")

    print("System is ready for STT.")

if __name__ == "__main__":
    asyncio.run(main())
