"""Unit tests for Grisha verdict parsing logic."""

import os
import sys

# Add src path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.agents.grisha import Grisha


class TestGrishaVerdictParsing:
    """Test cases for _fallback_verdict_analysis and _extract_verdict methods."""

    def setup_method(self):
        """Create Grisha instance for testing."""
        # Mock initialization to avoid LLM calls
        self.grisha = Grisha.__new__(Grisha)

    def test_explicit_success_with_error_context(self):
        """CRITICAL: Success verdict should win even when 'error' appears in context."""
        analysis = """
        The MCP tool returned error -32602 but this is an expected outcome.
        The step attempted to enumerate methods and the error indicates the tool is not available.
        For a discovery/analysis step, this is a valid outcome.
        
        КРОК ПІДТВЕРДЖЕНО
        """
        result = self.grisha._fallback_verdict_analysis(analysis, analysis.upper())
        assert result is True, "Expected True when explicit КРОК ПІДТВЕРДЖЕНО exists"

    def test_explicit_success_verdict_english(self):
        """Test English verdict markers."""
        analysis = "The step completed. VERDICT: CONFIRMED. All criteria met."
        result = self.grisha._fallback_verdict_analysis(analysis, analysis.upper())
        assert result is True, "Expected True for VERDICT: CONFIRMED"

    def test_explicit_failure_verdict(self):
        """Test explicit failure verdict."""
        analysis = "The file was not found. КРОК НЕ ПРОЙШОВ. Need retry."
        result = self.grisha._fallback_verdict_analysis(analysis, analysis.upper())
        assert result is False, "Expected False for КРОК НЕ ПРОЙШОВ"

    def test_success_indicator_without_failure(self):
        """Test success indicator in header."""
        analysis = "УСПІШНО: Directory created as expected."
        result = self.grisha._fallback_verdict_analysis(analysis, analysis.upper())
        assert result is True, "Expected True for УСПІШНО"

    def test_failure_indicator_only(self):
        """Test failure with no success context."""
        analysis = "ПОМИЛКА: Command failed to execute. Server unreachable."
        result = self.grisha._fallback_verdict_analysis(analysis, analysis.upper())
        assert result is False, "Expected False for ПОМИЛКА without success context"

    def test_acceptable_error_phrase_sanitization(self):
        """Test that 'acceptable error' phrases are sanitized."""
        analysis = "ПОМИЛКА Є ПРИЙНЯТНОЮ для цього кроку. ПІДТВЕРДЖЕНО."
        result = self.grisha._fallback_verdict_analysis(analysis, analysis.upper())
        assert result is True, "Expected True when error is marked as acceptable"

    def test_mcp_error_context(self):
        """Test MCP error in context doesn't break success verdict."""
        analysis = """
        Помилка MCP -32602 є очікуваною.
        VERDICT: CONFIRMED
        Step verified successfully.
        """
        result = self.grisha._fallback_verdict_analysis(analysis, analysis.upper())
        assert result is True, "Expected True when MCP error is in context but verdict is CONFIRMED"

    def test_reasoning_confirms_success(self):
        """Test reasoning phrases that confirm success."""
        analysis = "Analysis complete. Шлях існує і каталог створено правильно."
        result = self.grisha._fallback_verdict_analysis(analysis, analysis.upper())
        assert result is True, "Expected True when reasoning confirms success"

    def test_conflicting_indicators_success_wins(self):
        """Test that success indicators take priority over failure keywords."""
        analysis = "There was an error response but the task УСПІШНО completed."
        result = self.grisha._fallback_verdict_analysis(analysis, analysis.upper())
        assert result is True, "Expected True when УСПІШНО appears (success should win)"

    def test_no_clear_indicators_defaults_to_false(self):
        """Test default behavior with no clear indicators."""
        analysis = "The operation returned some data. Processing complete."
        result = self.grisha._fallback_verdict_analysis(analysis, analysis.upper())
        assert result is False, "Expected False when no clear indicators"

def run_tests():
    """Run all tests."""
    test = TestGrishaVerdictParsing()
    test.setup_method()

    tests = [
        ("explicit_success_with_error_context", test.test_explicit_success_with_error_context),
        ("explicit_success_verdict_english", test.test_explicit_success_verdict_english),
        ("explicit_failure_verdict", test.test_explicit_failure_verdict),
        ("success_indicator_without_failure", test.test_success_indicator_without_failure),
        ("failure_indicator_only", test.test_failure_indicator_only),
        ("acceptable_error_phrase_sanitization", test.test_acceptable_error_phrase_sanitization),
        ("mcp_error_context", test.test_mcp_error_context),
        ("reasoning_confirms_success", test.test_reasoning_confirms_success),
        ("conflicting_indicators_success_wins", test.test_conflicting_indicators_success_wins),
        ("no_clear_indicators_defaults_to_false", test.test_no_clear_indicators_defaults_to_false),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {name}: {e}")
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
