import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.agents.atlas import Atlas

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
    
    # 3. Test Local Code Discovery
    print("\nScenario 3: Local Code discovery & Analysis")
    # Providing more context in user request to help him find it directly
    query = "Знайди файл src/brain/orchestrator.py і на основі його вмісту поясни його роль?"
    analysis = await atlas.analyze_request(query)
    print(f"Intent detected: {analysis.get('intent')}")
    response = await atlas.chat(query)
    print(f"Atlas (Code Analyst): {response}")
    
    if "orchestrator" in response.lower() and ("клас" in response.lower() or "loop" in response.lower() or "trinity" in response.lower()):
        print("✓ Local Code test PASSED")
    else:
        print("⚠ Local Code test FAILED (Could not find or explain code)")

    # 4. Test Dynamic Tool Discovery (Spotlight/Calendar)
    print("\nScenario 4: Dynamic Tool Discovery (System Info)")
    # Ask for something that requires macos-use tools but wasn't hardcoded before
    query = "Перевір мій календар на сьогодні та знайди файли з назвою 'config' за допомогою Spotlight."
    analysis = await atlas.analyze_request(query)
    print(f"Intent detected: {analysis.get('intent')}")
    response = await atlas.chat(query)
    print(f"Atlas (System Info): {response}")
    
    if "календар" in response.lower() or "config" in response.lower() or "spotlight" in response.lower():
        print("✓ Dynamic Tool test PASSED")
    else:
        print("⚠ Dynamic Tool test FAILED (Could not use dynamic tools)")

if __name__ == "__main__":
    asyncio.run(test_chat_intelligence())
    asyncio.run(test_persona_intelligence())
