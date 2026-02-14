import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage

from src.providers.windsurf import WindsurfLLM


def benchmark_direct():
    print("🧪 Direct WindsurfLLM Benchmark...")

    # Models to test
    models = ["windsurf-fast", "swe-1.5", "deepseek-v3"]

    # Force direct mode
    os.environ["WINDSURF_DIRECT"] = "true"
    os.environ["WINDSURF_MODE"] = "direct"

    print(f"{'Model':<20} | {'Status':<10} | {'Time (s)':<8} | {'Preview'}")
    print("-" * 65)

    for model in models:
        start = time.time()
        try:
            llm = WindsurfLLM(model_name=model)
            messages = [HumanMessage(content="Hello! Who are you?")]

            # Use 30 second timeout for direct call
            response = llm.invoke(messages)
            elapsed = time.time() - start

            content = str(response.content).replace("\n", " ").strip()
            print(f"{model:<20} | SUCCESS    | {elapsed:>8.2f} | {content[:30]}...")
        except Exception as e:
            elapsed = time.time() - start
            print(f"{model:<20} | FAILED     | {elapsed:>8.2f} | {str(e)[:30]}...")


if __name__ == "__main__":
    benchmark_direct()
