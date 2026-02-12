import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Force load setup_dev to set environment if needed (or just ensure PYTHONPATH)
from src.brain.behavior.behavior_engine import behavior_engine
from src.brain.core.orchestration.error_router import error_router


def verify_config_loading():
    if not behavior_engine.config:
        sys.exit(1)

    patterns = behavior_engine.config.get("patterns", {}).get("adaptive_behavior", {})
    if "web_task_fallback" not in patterns:
        sys.exit(1)
    if "technical_audit_escalation" not in patterns:
        sys.exit(1)


def verify_web_fallback():
    # Context matching: task_type: web, repeated_failures: true
    context = {
        "task_type": "web",
        "repeated_failures": True,
        "step": {"action": "web_search", "tool": "search"},
        "attempt": 2,
    }

    strategy = error_router.decide("Connection error", attempt=2, context=context)

    if "Matched adaptive pattern: web_task_fallback" in strategy.reason:
        pass
    else:
        sys.exit(1)

    if strategy.action == "RETRY":
        pass
    else:
        sys.exit(1)


def verify_technical_audit():
    # Context: verification_failed: true, artifact_missing: true
    context = {
        "verification_failed": True,
        "artifact_missing": True,
        "step": {"action": "verify_artifact"},
        "attempt": 1,
    }

    strategy = error_router.decide("Verification failed", attempt=1, context=context)

    if "Matched adaptive pattern: technical_audit_escalation" in strategy.reason:
        pass
    else:
        sys.exit(1)

    if strategy.action == "VIBE_HEAL":
        pass
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        verify_config_loading()
        verify_web_fallback()
        verify_technical_audit()
    except Exception:
        sys.exit(1)
