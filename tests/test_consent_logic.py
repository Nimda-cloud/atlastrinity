import sys


# Mock the shared_context
class MockSharedContext:
    def to_dict(self):
        return {}

    @property
    def available_tools_summary(self):
        return "some tools"


sys.modules["..context"] = type("module", (), {"shared_context": MockSharedContext()})
sys.modules["..logger"] = type(
    "module", (), {"logger": type("logger", (), {"info": print, "error": print, "warning": print})}
)
sys.modules["..state_manager"] = type("module", (), {"state_manager": None})


def test_consent_logic():
    # Simulate the logic inside Tetyana.execute_step
    def is_consent(action, requires_consent=False):
        step_action_lower = str(action).lower()
        # The logic we just applied:
        return (
            "ask user" in step_action_lower
            or "request user consent" in step_action_lower
            or "await user approval" in step_action_lower
            or "get user confirmation" in step_action_lower
            or "confirm with user" in step_action_lower
            or ("confirm" in step_action_lower and "user" in step_action_lower)
            or ("approval" in step_action_lower and "user" in step_action_lower)
            or "preferences" in step_action_lower
            or requires_consent is True
        )

    test_cases = [
        (
            "Call filesystem_list_allowed_directories to confirm which directories this agent may read",
            False,
        ),
        ("Confirm with user before deleting the file", True),
        ("Ask user for their name", True),
        ("Request user consent for camera access", True),
        ("Confirm directory contents", False),
        ("Get user confirmation for the plan", True),
    ]

    for action, expected in test_cases:
        result = is_consent(action)
        print(f"Action: '{action}'")
        print(f"  Result: {result} | Expected: {expected}")
        assert result == expected, f"FAILED for '{action}'"

    print("\n✅ Consent logic test passed!")


if __name__ == "__main__":
    test_consent_logic()
