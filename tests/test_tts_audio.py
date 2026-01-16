import asyncio
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.brain.voice.tts import VoiceManager

async def test_minimal_tts():
    print("Initializing VoiceManager...")
    vm = VoiceManager()
    
    text = "Привіт! Це перевірка звуку. Якщо ви це чуєте, то ТТС працює правильно."
    print(f"Generating and playing: {text}")
    
    await vm.speak("atlas", text)
    print("Done.")

if __name__ == "__main__":
    asyncio.run(test_minimal_tts())
