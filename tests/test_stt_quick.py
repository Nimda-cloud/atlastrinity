import asyncio
import os
import sys
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.voice.stt import WhisperSTT


async def main():
    # Force tiny model for quick verification
    stt = WhisperSTT(model_name="tiny")
    print(f"Testing Whisper STT with model: {stt.model_name} on {stt.device}")

    print("Loading tiny model...")
    start = time.time()
    await stt.get_model()
    print(f"Tiny model loaded in {time.time() - start:.2f}s")

    print("Verification SUCCESS: Faster-Whisper engine is working.")


if __name__ == "__main__":
    asyncio.run(main())
