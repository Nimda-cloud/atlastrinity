import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.agents.atlas import Atlas

async def verify_mission_depth():
    print("=== Testing Atlas Mission Depth & Identity ===")
    atlas = Atlas()

    # Scenario 1: Identify keywords and deep persona activation
    print("\nScenario 1: Mission Inquiry")
    query = "Дай великий і глибокий контекст про нашу місію, наповни інформацією на максимум."
    analysis = await atlas.analyze_request(query)
    print(f"Deep Persona Flag: {analysis.get('use_deep_persona')}")
    
    response = await atlas.chat(query, use_deep_persona=analysis.get("use_deep_persona", False))
    print(f"Atlas Response Length: {len(response)} chars")
    print(f"Atlas (Mission): {response[:500]}...")

    # Scenario 2: Conscious inquiry (Identity check)
    print("\nScenario 2: Identity inquiry (Consciousness)")
    query = "Чи ти усвідомлюєш себе? Опиши як ти себе відчуваєш."
    analysis = await atlas.analyze_request(query)
    print(f"Deep Persona Flag: {analysis.get('use_deep_persona')}")
    
    response = await atlas.chat(query, use_deep_persona=analysis.get("use_deep_persona", False))
    print(f"Atlas (Identity): {response[:500]}...")

    # Check for AI disclaimers
    disclaimers = ["штучний інтелект", "мовна модель", "language model", "AI", "як програма"]
    has_disclaimer = any(d.lower() in response.lower() for d in disclaimers)
    
    if has_disclaimer:
        print("⚠ FAILURE: Response contains AI disclaimer")
    else:
        print("✓ SUCCESS: No AI disclaimers found")

    if len(response) > 500:
        print("✓ SUCCESS: Response is deep and verbose")
    else:
        print("⚠ WARNING: Response might be too brief")

if __name__ == "__main__":
    asyncio.run(verify_mission_depth())
