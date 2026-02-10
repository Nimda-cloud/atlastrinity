import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

# Force load setup_dev to set environment if needed (or just ensure PYTHONPATH)
from src.brain.behavior_engine import behavior_engine
from src.brain.error_router import error_router


def verify_config_loading():
    print(f"Config path: {behavior_engine.config_path}")
    if not behavior_engine.config:
        print("ERROR: Behavior config not loaded!")
        sys.exit(1)

    patterns = behavior_engine.config.get("patterns", {}).get("adaptive_behavior", {})
    print(f"Loaded {len(patterns)} adaptive behavior patterns.")
    if "web_task_fallback" not in patterns:
        print("ERROR: 'web_task_fallback' pattern missing from config!")
        sys.exit(1)
    if "technical_audit_escalation" not in patterns:
        print("ERROR: 'technical_audit_escalation' pattern missing from config!")
        sys.exit(1)
    print("✓ Config loading verified.")


def verify_web_fallback():
    print("\nTesting 'web_task_fallback' pattern match...")
    # Context matching: task_type: web, repeated_failures: true
    context = {
        "task_type": "web",
        "repeated_failures": True,
        "step": {"action": "web_search", "tool": "search"},
        "attempt": 2,
    }

    strategy = error_router.decide("Connection error", attempt=2, context=context)
    print(f"Strategy returned: {strategy.action} (Reason: {strategy.reason})")

    if "Matched adaptive pattern: web_task_fallback" in strategy.reason:
        print("✓ Pattern matched correctly.")
    else:
        print("✗ Pattern match failed.")
        sys.exit(1)

    if strategy.action == "RETRY":
        print("✓ Action mapped to RETRY (heuristic).")
    else:
        print(f"✗ Unexpected action mapping: {strategy.action}")
        sys.exit(1)


def verify_technical_audit():
    print("\nTesting 'technical_audit_escalation' pattern match...")
    # Context: verification_failed: true, artifact_missing: true
    context = {
        "verification_failed": True,
        "artifact_missing": True,
        "step": {"action": "verify_artifact"},
        "attempt": 1,
    }

    strategy = error_router.decide("Verification failed", attempt=1, context=context)
    print(f"Strategy returned: {strategy.action} (Reason: {strategy.reason})")

    if "Matched adaptive pattern: technical_audit_escalation" in strategy.reason:
        print("✓ Pattern matched correctly.")
    else:
        print("✗ Pattern match failed.")
        sys.exit(1)

    if strategy.action == "VIBE_HEAL":
        print("✓ Action mapped to VIBE_HEAL (heuristic).")
    else:
        print(f"✗ Unexpected action mapping: {strategy.action}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        verify_config_loading()
        verify_web_fallback()
        verify_technical_audit()
        print("\nAll verifications passed!")
    except Exception as e:
        print(f"\nCRITICAL FAILURE: {e}")
        sys.exit(1)
