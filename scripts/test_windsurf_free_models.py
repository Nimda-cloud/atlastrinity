"""
Test Windsurf provider with free models.

This script tests the Windsurf provider with all available free models.
It will try each model and report the results.

Usage:
    python scripts/test_windsurf_free_models.py

Environment variables:
    WINDSURF_API_KEY: Your Windsurf API key (required)
    WINDSURF_MODE: Set to 'local', 'direct', or 'proxy' (default: auto-detect)
"""

import os
import sys
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage, SystemMessage

from providers.windsurf import WindsurfLLM, _detect_language_server, _ls_heartbeat

# Free models to test
FREE_MODELS = [
    "deepseek-v3",
    "deepseek-r1",
    "swe-1",
    "grok-code-fast-1",
    "kimi-k2.5",
]

# Test prompt
TEST_PROMPT = """
Please provide a brief response to the following question:
What is the capital of France? Also, what is 5+7?

Your response should be in this exact format:
Capital: [capital]
Sum: [sum]
"""


def test_model(model_name: str, mode: str | None = None) -> tuple[bool, str]:
    """Test a single model with the given mode."""
    print(f"\n{'=' * 80}")
    print(f"Testing model: {model_name}" + (f" (mode: {mode})" if mode else ""))
    print("-" * 80)

    start_time = time.time()

    try:
        # Set mode if specified
        if mode:
            os.environ["WINDSURF_MODE"] = mode

        # Initialize the model
        llm = WindsurfLLM(model_name=model_name)

        # Make the API call
        response = llm.invoke(
            [
                SystemMessage(content="You are a helpful assistant. Be concise and accurate."),
                HumanMessage(content=TEST_PROMPT),
            ]
        )

        # Process the response
        # Ensure content is a string before calling strip()
        content = (
            str(response.content).strip() if hasattr(response, "content") else str(response).strip()
        )
        elapsed = time.time() - start_time

        print(f"Response ({elapsed:.2f}s):")
        print("-" * 40)
        print(content)
        print("-" * 40)

        # Simple validation of response format
        if "Capital:" in content and "Sum:" in content:
            print("✅ Response format looks good!")
            return True, content
        print("⚠️  Response format doesn't match expected format")
        return False, content

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"Error after {elapsed:.2f}s: {e!s}"
        print(f"❌ {error_msg}")
        return False, error_msg

    finally:
        # Clean up environment variable
        os.environ.pop("WINDSURF_MODE", None)


def main():
    print("Windsurf Free Models Test")
    print("=" * 80)

    # Check API key
    api_key = os.environ.get("WINDSURF_API_KEY")
    if not api_key:
        print("ERROR: WINDSURF_API_KEY environment variable is required")
        print("Run: python -m providers.get_windsurf_token")
        sys.exit(1)

    # Get mode from env or auto-detect
    mode = os.environ.get("WINDSURF_MODE")
    if not mode:
        # Try to auto-detect LS
        port, csrf = _detect_language_server()
        if port and csrf and _ls_heartbeat(port, csrf):
            mode = "local"
        else:
            mode = "direct"  # Fall back to direct mode

    print(f"Using mode: {mode}")
    print(f"Testing {len(FREE_MODELS)} free models")

    # Test each model
    results = {}
    for model in FREE_MODELS:
        success, response = test_model(model, mode)
        results[model] = {
            "success": success,
            "response": response,
        }

    # Print summary
    print("\n" + "=" * 80)
    print("Test Summary:")
    print("=" * 80)

    success_count = sum(1 for r in results.values() if r["success"])
    print(f"✅ {success_count}/{len(results)} models succeeded")

    for model, result in results.items():
        status = "✅" if result["success"] else "❌"
        print(f"{status} {model}")
        if not result["success"]:
            print(f"   Error: {result['response']}")


if __name__ == "__main__":
    main()
