"""
Minimal test for Windsurf provider with free models.

This script tests the Windsurf provider with a single free model
using only essential dependencies.

Usage:
    python3 scripts/test_windsurf_minimal.py

Environment variables:
    WINDSURF_API_KEY: Your Windsurf API key (required)
"""

import os
import sys
import time

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from src.providers.windsurf import WindsurfLLM
except ImportError:
    sys.exit(1)

# Test with a single free model
TEST_MODEL = "deepseek-v3"  # Using a single free model to minimize dependencies


def main():

    # Check API key
    api_key = os.environ.get("WINDSURF_API_KEY")
    if not api_key:
        sys.exit(1)

    try:
        # Initialize the model with direct mode to avoid LS detection
        llm = WindsurfLLM(model_name=TEST_MODEL)

        # Simple test prompt
        prompt = "What is the capital of France? Answer in one word."

        # Make the API call
        start_time = time.time()
        response = llm.invoke([{"role": "user", "content": prompt}])
        time.time() - start_time

        # Process the response
        if hasattr(response, "content"):
            str(response.content)
        else:
            str(response)

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
