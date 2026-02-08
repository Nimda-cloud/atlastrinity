import sys


class MockSharedContext:
    def to_dict(self):
        return {}

    @property
    def available_tools_summary(self):
        return "some tools"

import types

m_context = types.ModuleType("context")
m_context.shared_context = MockSharedContext()  # type: ignore
sys.modules["..context"] = m_context

m_logger = types.ModuleType("logger")
m_logger.logger = type("logger", (), {"info": print, "error": print, "warning": print})()  # type: ignore
sys.modules["..logger"] = m_logger

m_state = types.ModuleType("state_manager")
m_state.state_manager = None  # type: ignore
sys.modules["..state_manager"] = m_state

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
