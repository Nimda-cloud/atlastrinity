"""
ContextCheck: Logic Validation Module for DevTools MCP.

This module validates LLM outputs against expected logical conditions defined in YAML/JSON test scenarios.
"""

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, TypedDict, Union, cast

import yaml


# Types
class Expectation(TypedDict):
    """Definition of a single expectation check."""
    type: Literal["contains", "not_contains", "regex", "json_field", "exact"]
    value: Any
    key: str | None  # For json_field checks


class TestScenario(TypedDict):
    """Definition of a single test scenario."""
    name: str
    description: str | None
    input: str
    expected: list[Expectation]


class TestResult(TypedDict):
    """Result of a single test execution."""
    name: str
    passed: bool
    input: str
    output: str
    failures: list[str]


def load_tests(file_path: str | Path) -> list[TestScenario]:
    """Load test scenarios from a YAML or JSON file."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Test file not found: {path}")

    with open(path, encoding="utf-8") as f:
        if path.suffix in [".yaml", ".yml"]:
            data = yaml.safe_load(f)
        elif path.suffix == ".json":
            data = json.load(f)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    # Support specific "tests" key or root list
    if isinstance(data, dict) and "tests" in data:
        return cast(list[TestScenario], data["tests"])
    if isinstance(data, list):
        return cast(list[TestScenario], data)
    
    raise ValueError("Invalid test file structure. Expected list of tests or {'tests': [...]}")


def validate_output(output: str, expectations: list[Expectation]) -> list[str]:
    """Validate output string against a list of expectations.
    
    Returns:
        List of failure messages. Empty list means all passed.
    """
    failures = []

    for exp in expectations:
        check_type = exp.get("type")
        value = exp.get("value")

        if check_type == "contains":
            if value not in output:
                failures.append(f"Expected to contain '{value}'")

        elif check_type == "not_contains":
            if value in output:
                failures.append(f"Expected NOT to contain '{value}'")

        elif check_type == "regex":
            if not re.search(str(value), output, re.MULTILINE):
                failures.append(f"Expected to match regex '{value}'")

        elif check_type == "exact":
            if output.strip() != str(value).strip():
                failures.append(f"Expected exact match '{value}'")
                
        elif check_type == "json_field":
            key = exp.get("key")
            if not key:
                failures.append("Missing 'key' for json_field check")
                continue
                
            try:
                # Try to extract JSON from output (first brace to last brace)
                json_match = re.search(r"(\{.*\})", output, re.DOTALL)
                if not json_match:
                    failures.append("Could not find valid JSON in output")
                    continue
                    
                json_data = json.loads(json_match.group(1))
                actual_val = json_data.get(key)
                
                if actual_val != value:
                    failures.append(f"JSON field '{key}': expected '{value}', got '{actual_val}'")
                    
            except json.JSONDecodeError:
                failures.append("Failed to parse JSON in output")
            except Exception as e:
                failures.append(f"JSON check error: {e}")

        else:
            failures.append(f"Unknown check type: {check_type}")

    return failures


def run_test_suite(test_file: str, runner_func: Callable[[str], str] | None = None) -> dict[str, Any]:
    """Run a full test suite.
    
    Args:
        test_file: Path to the test definition file.
        runner_func: A function that takes (input_str) and returns (output_str).
                     If None, it returns a 'dry run' status or error.
                     
    Returns:
        Summary dictionary with results.
    """
    try:
        tests = load_tests(test_file)
    except Exception as e:
        return {"error": str(e)}

    results = []
    passed_count = 0

    if not runner_func:
        return {
            "status": "dry_run",
            "message": "Tests loaded successfully but no runner provided.",
            "test_count": len(tests),
            "tests": tests
        }

    for test in tests:
        test_name = test.get("name", "Unnamed Test")
        inp = test.get("input", "")
        expectations = test.get("expected", [])
        
        try:
            # Execute the 'runner' (LLM call or mocked)
            output = runner_func(inp)
            
            fail_msgs = validate_output(output, expectations)
            passed = len(fail_msgs) == 0
            
            if passed:
                passed_count += 1
                
            results.append({
                "name": test_name,
                "passed": passed,
                "failures": fail_msgs,
                "input_preview": f"{inp[:50]}...",
                "output_preview": f"{output[:50]}..."
            })
            
        except Exception as e:
            results.append({
                "name": test_name,
                "passed": False,
                "failures": [f"Runner exception: {e}"]
            })

    return {
        "total": len(tests),
        "passed": passed_count,
        "failed": len(tests) - passed_count,
        "results": results
    }
