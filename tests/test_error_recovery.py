from unittest.mock import MagicMock, patch

import pytest

from src.brain.error_router import ErrorCategory, RecoveryStrategy, SmartErrorRouter


@pytest.fixture
def error_router():
    return SmartErrorRouter()


def test_decide_logic_error_returns_vibe_heal(error_router):
    """Verify that LOGIC errors now return VIBE_HEAL instead of SELF_HEALING."""
    strategy = error_router.decide("SyntaxError: invalid syntax", attempt=1)

    assert strategy.action == "VIBE_HEAL"
    assert strategy.context_needed is True
    assert "Self-Healing Protocol" in strategy.reason


def test_decide_uses_behavior_engine_patterns(error_router):
    """Verify that behavior_engine patterns override default logic."""

    # Mock pattern
    mock_pattern = MagicMock()
    mock_pattern.name = "test_pattern"
    mock_pattern.action = {"strategy_action": "CUSTOM_ACTION", "backoff": 5.0, "max_retries": 10}

    # Mock behavior_engine
    with patch("src.brain.behavior_engine.behavior_engine") as mock_engine:
        mock_engine.match_pattern.return_value = mock_pattern

        context = {"task_type": "test_task"}
        strategy = error_router.decide("Some Error", attempt=1, context=context)

        # Verify match_pattern was called with correct context
        expected_ctx = context.copy()
        expected_ctx["error"] = "Some Error"
        expected_ctx["attempt"] = 1
        expected_ctx["error_contains"] = "Some Error"
        mock_engine.match_pattern.assert_called_with(expected_ctx, "adaptive_behavior")

        # Verify result logic
        assert strategy.action == "CUSTOM_ACTION"
        assert strategy.backoff == 5.0
        assert strategy.max_retries == 10
        assert "Matched adaptive pattern: test_pattern" in strategy.reason


def test_decide_fallback_heuristics(error_router):
    """Verify fallback heuristics for patterns without explicit strategy_action."""

    # Mock pattern for Vibe server
    mock_pattern_vibe = MagicMock()
    mock_pattern_vibe.name = "vibe_pattern"
    mock_pattern_vibe.action = {"server": "vibe"}

    with patch("src.brain.behavior_engine.behavior_engine") as mock_engine:
        mock_engine.match_pattern.return_value = mock_pattern_vibe

        strategy = error_router.decide("Some Error", attempt=1)
        assert strategy.action == "VIBE_HEAL"

    # Mock pattern for sudo (Ask User)
    mock_pattern_sudo = MagicMock()
    mock_pattern_sudo.name = "sudo_pattern"
    mock_pattern_sudo.action = {"retry_with_sudo": True}

    with patch("src.brain.behavior_engine.behavior_engine") as mock_engine:
        mock_engine.match_pattern.return_value = mock_pattern_sudo

        strategy = error_router.decide("Permission denied", attempt=1)
        assert strategy.action == "ASK_USER"


def test_verify_recursion_detection(error_router):
    """Verify recursion detection returns ASK_USER."""
    error = "grisha recursion detected in verification loop"
    strategy = error_router.decide(error, attempt=1)

    # Should classify as VERIFICATION but detect recursion
    assert strategy.action == "ASK_USER"
    assert "recursion loop" in strategy.reason
