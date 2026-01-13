
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.config_loader import config
from src.brain.agents.tetyana import Tetyana

def verify_config():
    print("--- Verifying Tetyana Model Configuration ---")
    
    # 1. Check Config Loader Defaults
    agent_config = config.get_agent_config("tetyana")
    print(f"Config Loader 'model': {agent_config.get('model')}")
    print(f"Config Loader 'reasoning_model': {agent_config.get('reasoning_model')}")
    
    # 2. Check Instance
    # We need to mock CopilotLLM to avoid API key errors if not set
    # But for now let's just see if it initializes without error or check attributes
    try:
        tetyana = Tetyana()
        print(f"Tetyana.llm.model_name: {tetyana.llm.model_name}")
        print(f"Tetyana.reasoning_llm.model_name: {tetyana.reasoning_llm.model_name}")
        
        if tetyana.reasoning_llm.model_name in ["gpt-4o", "gpt-4.1"]:
            print("SUCCESS: Reasoning model is correctly set to a strong model.")
        else:
            print(f"FAILURE: Reasoning model is {tetyana.reasoning_llm.model_name}")
            
    except Exception as e:
        print(f"Error initializing Tetyana: {e}")

if __name__ == "__main__":
    verify_config()
