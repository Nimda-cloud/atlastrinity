import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.agents.atlas import Atlas
from src.brain.orchestrator import Trinity
from langchain_core.messages import HumanMessage

async def test_chat_intelligence():
    print("=== Testing Capable Chat Intelligence ===")
    atlas = Atlas()
    
    # Scenario 1: Greeting (Simple Chat)
    print("\nScenario 1: Greeting")
    analysis = await atlas.analyze_request("Привіт, як справи?")
    print(f"Intent detected: {analysis.get('intent')} (Reason: {analysis.get('reason')})")
    
    # Scenario 2: Information Seeking (News/Weather - should be 'chat' now)
    print("\nScenario 2: Information Seeking (News)")
    analysis = await atlas.analyze_request("Яка зараз погода в Києві та останні новини?")
    print(f"Intent detected: {analysis.get('intent')} (Reason: {analysis.get('reason')})")
    
    # Scenario 3: Code Explanation (Information Seeking)
    print("\nScenario 3: Code Explanation")
    analysis = await atlas.analyze_request("Поясни, як працює скрипт setup_dev.py?")
    print(f"Intent detected: {analysis.get('intent')} (Reason: {analysis.get('reason')})")
    
    # Scenario 4: Task intent (State change - should still be 'task')
    print("\nScenario 4: State Change (Task)")
    analysis = await atlas.analyze_request("Створи файл test.txt на робочому столі")
    print(f"Intent detected: {analysis.get('intent')} (Reason: {analysis.get('reason')})")

async def test_persona_intelligence():
    print("\n=== Testing Adaptive Persona Intelligence ===")
    atlas = Atlas()
    
    # 1. Test Brevity (Greeting)
    print("\nScenario 1: Simple Greeting (Brevity)")
    analysis = await atlas.analyze_request("Привіт")
    print(f"Deep Persona Flag: {analysis.get('use_deep_persona')}")
    response = await atlas.chat("Привіт", use_deep_persona=analysis.get('use_deep_persona', False))
    print(f"Atlas (Brief): {response}")
    
    # 2. Test Deep Persona (Identity)
    print("\nScenario 2: Identity & Mission (Deep)")
    analysis = await atlas.analyze_request("Розкажи про свою місію та хто тебе створив?")
    print(f"Deep Persona Flag: {analysis.get('use_deep_persona')}")
    response = await atlas.chat("Розкажи про свою місію та хто тебе створив?", use_deep_persona=analysis.get('use_deep_persona', False))
    print(f"Atlas (Deep): {response}")
    
    if analysis.get('use_deep_persona') == True and "Олег" in response:
        print("✓ Deep Persona test PASSED")
    else:
        print("⚠ Deep Persona test FAILED (Flag not set or missing context)")

if __name__ == "__main__":
    asyncio.run(test_chat_intelligence())
    asyncio.run(test_persona_intelligence())
