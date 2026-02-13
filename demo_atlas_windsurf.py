
import asyncio
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.getcwd())

from src.providers.windsurf import WindsurfLLM
from langchain_core.messages import HumanMessage

async def main():
    print("--- Atlas Trinity: Windsurf Integration Demo ---")
    
    # 1. Initialize Provider
    print("[1] Initializing WindsurfLLM provider...")
    # Credentials are auto-loaded from .env by the provider, but we ensure mode is set
    os.environ["WINDSURF_MODE"] = "cascade" 
    
    try:
        llm = WindsurfLLM(
            model_id="deepseek-v3", # Explicitly use the model we found
            temperature=0.0
        )
    except Exception as e:
        print(f"[ERROR] Failed to initialize WindsurfLLM: {e}")
        return

    # 2. Prepare Prompt
    prompt = (
        "You are an expert Python coder. Create a modern, stylish GUI calculator in Python using tkinter. "
        "Use a dark theme (black/grey background) with orange accent buttons. "
        "Output ONLY the raw Python code, no markdown formatting."
    )
    print(f"\n[2] Sending prompt to Windsurf (Mode: {llm._mode})...")
    print(f"    Prompt: {prompt[:60]}...")

    # 3. Generate
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        code = response.content
        
        # Clean markdown if present
        if code.startswith("```python"):
            code = code.split("\n", 1)[1]
        if code.endswith("```"):
            code = code.rsplit("\n", 1)[0]
            
        print("\n[3] Received response from Windsurf!")
        print(f"    Length: {len(code)} chars")
        
        # 4. Save Artifact
        print("\n[4] Saving artifact to 'calculator.py'...")
        with open("calculator.py", "w") as f:
            f.write(code)
        print("    Success!")
        
    except Exception as e:
        print(f"\n[ERROR] Generation failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
