import os
import sys
import time

from langchain_core.messages import HumanMessage, SystemMessage

from providers.windsurf import WindsurfLLM

print(f"Using Python {sys.version}")

# Configuration
MODEL_NAME = "deepseek-v3"
API_KEY = os.getenv('WINDSURF_API_KEY')

if not API_KEY:
    print("ERROR: WINDSURF_API_KEY environment variable not set")
    print("Get your API key from the Windsurf dashboard and run:")
    print("export WINDSURF_API_KEY='your_api_key_here'")
    sys.exit(1)

print(f"Testing Windsurf Cascade flow with model: {MODEL_NAME}")
print("="*60)

# Create LLM instance with cascade mode
llm = WindsurfLLM(
    model_name=MODEL_NAME,
    api_key=API_KEY,
    direct_mode=False
)

# Prepare messages
messages = [
    SystemMessage(content="Ти корисний асистент. Відповідай українською."),
    HumanMessage(content="Опиши, як працює Cascade pipeline у Windsurf провайдері?")
]

# Run test
print("Sending request through Cascade pipeline...")
start_time = time.time()

try:
    response = llm.invoke(messages)
    elapsed = time.time() - start_time
    
    print(f"\nResponse received in {elapsed:.2f} seconds")
    print("-"*60)
    print(response.content)
    print("-"*60)
    print("✅ Test successful! Cascade pipeline is working with free model.")

except Exception as e:
    print(f"\n❌ Test failed: {e!s}")
    print("Possible solutions:")
    print("1. Ensure language_server_macos_arm is running")
    print("2. Verify your API key has sufficient quota")
    print("3. Check network/firewall settings")
    sys.exit(1)
