"""AtlasTrinity Error Router

Intelligent error classification and recovery routing system.
Acts as the 'Triaging Doctor' for exceptions during task execution.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .logger import logger


class ErrorCategory(Enum):
    """Categories of errors requiring distinct recovery strategies"""

    TRANSIENT = "transient"  # Network blips, timeouts (Retry)
    INFRASTRUCTURE = "infrastructure"  # API rate limits, service unavailability (Wait and Retry)
    LOGIC = "logic"  # Code bugs, syntax errors (Vibe Fix)
    STATE = "state"  # Corrupted session/environment (Restart)
    PERMISSION = "permission"  # Access denied (Ask User/Atlas)
    USER_INPUT = "user_input"  # Missing info (Ask User)
    VERIFICATION = "verification"  # Grisha's verification logic failed (Immediate escalation)
    UNKNOWN = "unknown"  # Unclassified (Default fallback)


@dataclass
class RecoveryStrategy:
    """Action plan for recovering from an error"""

    action: str  # RETRY, VIBE_HEAL, RESTART, ASK_USER
    backoff: float = 0.0
    max_retries: int = 3
    context_needed: bool = False  # Does Vibe need logs/context?
    reason: str = ""


class SmartErrorRouter:
    """Routes exceptions to the optimal recovery strategy"""

    # Transient: simple retries usually fix these
    TRANSIENT_PATTERNS = [
        r"connection\s+(refused|reset|timeout)",
        r"timeout",
        r"broken\s+pipe",
        r"network\s+error",
        r"socket\s+error",
        r"temporary\s+failure",
    ]

    # Infrastructure: API limits, service issues (requires longer wait)
    INFRASTRUCTURE_PATTERNS = [
        r"rate\s+limit\s+exceeded",
        r"mistral\s+api\s+rate\s+limit",
        r"error_type.*RATE_LIMIT",
        r"api\s+quota\s+exceeded",
        r"too\s+many\s+requests",
        r"429\s+too\s+many\s+requests",
        r"503\s+service\s+unavailable",
        r"502\s+bad\s+gateway",
        r"api\s+is\s+unreachable",
    ]

    # Logic: requires code modification (Vibe)
    LOGIC_PATTERNS = [
        r"syntax\s+error",
        r"name\s+error",
        r"type\s+error",
        r"attribute\s+error",
        r"key\s+error",
        r"index\s+error",
        r"value\s+error",
        r"assertion\s+error",
        r"import\s+error",
        r"module\s+not\s+found",
        r"indentation\s+error",
        r"unbound\s+local\s+error",
    ]

    # State: requires system restart/reload
    STATE_PATTERNS = [
        r"corrupted\s+state",
        r"session\s+expired",
        r"invalid\s+token",
        r"database\s+locked",
        r"deadlock",
        r"stale\s+file\s+handle",
        r"transport\s+endpoint\s+is\s+not\s+connected",
    ]

    # Permission: requires intervention
    PERMISSION_PATTERNS = [
        r"permission\s+denied",
        r"access\s+denied",
        r"401\s+unauthorized",
        r"403\s+forbidden",
    ]

    # Verification: Grisha's verification system detected issues
    VERIFICATION_PATTERNS = [
        r"grisha\s+rejected",
        r"auto-verdict\s+after",
        r"verification.*failed",
        r"max\s+attempts\s+reached.*verification",
        r"0/\d+\s+successful",
    ]

    def __init__(self):
        self._cache = {}

    def classify(self, error: str) -> ErrorCategory:
        """Classifies an error string into a category"""
        error_str = str(error).lower()
        if error_str in self._cache:
            return self._cache[error_str]

        category = ErrorCategory.UNKNOWN

        # Check infrastructure first (API rate limits should not be treated as transient)
        if any(re.search(p, error_str) for p in self.INFRASTRUCTURE_PATTERNS):
            category = ErrorCategory.INFRASTRUCTURE
        elif any(re.search(p, error_str) for p in self.VERIFICATION_PATTERNS):
            category = ErrorCategory.VERIFICATION
        elif any(re.search(p, error_str) for p in self.TRANSIENT_PATTERNS):
            category = ErrorCategory.TRANSIENT
        elif any(re.search(p, error_str) for p in self.LOGIC_PATTERNS):
            category = ErrorCategory.LOGIC
        elif any(re.search(p, error_str) for p in self.STATE_PATTERNS):
            category = ErrorCategory.STATE
        elif any(re.search(p, error_str) for p in self.PERMISSION_PATTERNS):
            category = ErrorCategory.PERMISSION
        elif "need_user_input" in error_str:
            category = ErrorCategory.USER_INPUT

        self._cache[error_str] = category
        return category

    def decide(self, error: Any, attempt: int = 1) -> RecoveryStrategy:
        """Decides the recovery strategy based on error and attempt count"""
        category = self.classify(str(error))

        logger.info(f"[ROUTER] Error classified as: {category.value} (Attempt {attempt})")

        if category == ErrorCategory.INFRASTRUCTURE:
            # Infrastructure issues: wait longer, don't involve Vibe/Grisha
            # These are external service issues, not code problems
            if attempt <= 3:
                return RecoveryStrategy(
                    action="WAIT_AND_RETRY",
                    backoff=60.0 * attempt,  # 60s, 120s, 180s
                    max_retries=3,
                    reason=f"API rate limit or service unavailability detected. Waiting {60 * attempt}s before retry.",
                )
            else:
                # After 3 attempts, notify user
                return RecoveryStrategy(
                    action="ASK_USER",
                    reason="Persistent API rate limiting after multiple retries. Manual intervention may be needed.",
                )

        if category == ErrorCategory.TRANSIENT:
            # Patient Retry
            backoff = 2.0 * attempt
            return RecoveryStrategy(
                action="RETRY",
                backoff=backoff,
                max_retries=5,
                reason="Transient network/system issue. Retrying with backoff.",
            )

        if category == ErrorCategory.LOGIC:
            # Fast Fail -> Vibe Heal
            # We skip simple retries for logic errors because re-running buggy code won't fix it
            return RecoveryStrategy(
                action="VIBE_HEAL",
                backoff=0.0,
                max_retries=2,  # Give Vibe 2 shots using Reflection
                context_needed=True,
                reason="Logic error detected. Engaging Vibe for code repair.",
            )

        if category == ErrorCategory.STATE:
            # Immediate Restart
            return RecoveryStrategy(
                action="RESTART", reason="System state corruption detected. Restarting application."
            )

        if category == ErrorCategory.PERMISSION:
            return RecoveryStrategy(
                action="ASK_USER", reason="Permission denied. Creating manual request."
            )

        if category == ErrorCategory.VERIFICATION:
            # ENHANCED: Distinguish between legitimate step failure vs verification system bug
            error_str = str(error).lower()
            
            # Legitimate step failures (NOT verification system bugs):
            legitimate_failure_indicators = [
                "empty results detected",
                "verification criteria not met",
                "no design files found",
                "artifact not found",
                "expected result not achieved",
                "tool execution found but result empty"
            ]
            
            # True verification system bugs (require Atlas diagnostic):
            system_bug_indicators = [
                "grisha crashed",
                "verification logic error",
                "sequential thinking failed",
                "tool routing loop",
                "infinite verification recursion",
                "verification timeout after"
            ]
            
            # Check if this is a legitimate failure (step didn't produce expected result)
            is_legitimate_failure = any(indicator in error_str for indicator in legitimate_failure_indicators)
            is_system_bug = any(indicator in error_str for indicator in system_bug_indicators)
            
            if is_legitimate_failure and not is_system_bug:
                # This is a REAL step failure, not a verification bug
                # Let Tetyana retry with adjustments
                logger.info("[ROUTER] Detected legitimate step failure (not verification bug)")
                return RecoveryStrategy(
                    action="RETRY",
                    backoff=2.0,
                    max_retries=2,
                    reason="Step verification failed due to missing expected results. Retrying with adjusted approach.",
                )
            else:
                # True verification system failure - escalate to Atlas
                return RecoveryStrategy(
                    action="ATLAS_PLAN",
                    context_needed=True,
                    reason="Verification system failure detected. This indicates issues with Grisha's error detection logic, not the task itself. Escalating for diagnostic review.",
                )

        # Unknown / Default Fallback
        if attempt <= 2:
            return RecoveryStrategy(
                action="RETRY", backoff=1.0, reason="Unknown error. Trying again."
            )
        else:
            # If 2 simple retries failed, assume it's complex and ask Vibe/Atlas
            return RecoveryStrategy(
                action="ATLAS_PLAN",
                context_needed=True,
                reason="Persistent unknown error. Escalating to Atlas.",
            )


# Global Instance
error_router = SmartErrorRouter()
