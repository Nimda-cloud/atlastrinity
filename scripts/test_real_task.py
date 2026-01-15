
import asyncio
import os
import sys
import logging

# Ensure src is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(root_dir, "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from src.brain.orchestrator import Trinity

async def main():
    print("--- STARTING REAL TASK SIMULATION ---")
    
    # Initialize Orchestrator
    trinity = Trinity()
    await trinity.initialize()
    
    # Define a real, safe task
    task = "Create a file named 'dev_mode_test.txt' in the current directory with the text 'AtlasTrinity Dev Test Successful', then check if it exists."
    
    print(f"Task: {task}")
    
    # Execute
    try:
        result = await trinity.run(task)
        print("\n--- EXECUTION FINISHED ---")
        print(f"Status: {result.get('status')}")
        
        # summary of steps
        steps = result.get("result", [])
        if isinstance(steps, list):
            for step in steps:
                print(f"\nStep: {step.get('action')}")
                print(f"Success: {step.get('success')}")
                print(f"Result: {step.get('result')}")
                print(f"Error: {step.get('error')}")
        else:
            print(f"Result payload: {steps}")
            
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
