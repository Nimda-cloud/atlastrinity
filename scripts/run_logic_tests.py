"""
Script to run logic tests using the new ContextCheck module.
"""

import json
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

from mcp_server.context_check import run_test_suite


def mock_runner(input_str: str) -> str:
    """Mock LLM/System runner for testing purposes."""
    if "Hello" in input_str:
        return "Hello user! How can I help?"
    if "JSON" in input_str:
        return '{"status": "success", "data": []}'
    return "I don't understand."

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_logic_tests.py <test_file>")
        sys.exit(1)

    test_file = sys.argv[1]
    print(f"Running tests from: {test_file}")

    # Run with mock runner
    results = run_test_suite(test_file, runner_func=mock_runner)

    print(json.dumps(results, indent=2))

    if results.get("failed", 0) > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
