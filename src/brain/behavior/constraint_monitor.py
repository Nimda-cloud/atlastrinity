"""Constraint Monitor

Periodically checks system logs against user-defined constraints.
Triggers priority parallel healing if violations are detected.
"""

import os

from src.brain.config import BRAIN_DIR
from src.brain.healing.parallel_healing import parallel_healing_manager
from src.brain.monitoring.logger import logger

CONSTRAINTS_FILE = os.path.join(BRAIN_DIR, "data", "user_constraints.txt")


class ConstraintMonitor:
    """Monitors system behavior against user constraints."""

    def __init__(self):
        self._last_check_logs: list[dict] = []
        self._is_running = False

    async def check_compliance(self, log_context: str, recent_logs: list[dict]) -> None:
        """
        Check if recent logs violate any user constraints.
        This is a non-blocking check.
        """
        if self._is_running:
            return

        try:
            self._is_running = True

            # 1. Read constraints
            constraints = self._read_constraints()
            if not constraints:
                return

            # 2. optimize: only check if we have new logs
            if not recent_logs or recent_logs == self._last_check_logs:
                return

            self._last_check_logs = recent_logs[-20:]  # Keep small history to detect duplicates

            # 3. Check if system is configured for Ukrainian voice output (bilingual operation)
            # If so, skip the language constraint check as Ukrainian voice is expected and legitimate
            from src.brain.config.config_loader import config

            voice_language = config.get("voice.language", "uk")

            # Filter out language-related constraints if Ukrainian voice is configured
            filtered_constraints = []
            for constraint in constraints:
                # Skip language constraint if system is designed for Ukrainian voice
                if (
                    "language" in constraint.lower()
                    and "ukrainian" in constraint.lower()
                    and voice_language == "uk"
                ):
                    logger.debug(
                        f"[CONSTRAINT_MONITOR] Skipping language constraint - Ukrainian voice is configured: {constraint}"
                    )
                    continue
                filtered_constraints.append(constraint)

            if not filtered_constraints:
                logger.debug("[CONSTRAINT_MONITOR] No applicable constraints after filtering")
                return

            # Prepare check prompt
            constraints_str = "\n".join([f"- {c}" for c in filtered_constraints])

            prompt = f"""CONSTRAINT CHECK
            
            Analyze these recent system logs against the following strict user constraints.
            
            USER CONSTRAINTS:
            {constraints_str}
            
            RECENT LOGS:
            {log_context[-3000:]}
            
            If any constraint is VIOLATED, report it. If all adhere, reply "COMPLIANT".
            
            If violated, format response as:
            VIOLATION: [Constraint description]
            EVIDENCE: [Log line or observation]
            """

            # 3. Analyze with a generic LLM (not Vibe, to save rate limits)
            # We'll use the Atlas agent's LLM or a generic one from shared_context
            from src.brain.agents.atlas import Atlas

            audit_agent = Atlas()

            # Use a lighter/cheaper model for auditing if possible,
            # or just the default one which usually has higher limits than Mistral Vibe
            result_text = await audit_agent.llm.ainvoke(prompt)
            if hasattr(result_text, "content"):
                result_text = str(result_text.content)
            else:
                result_text = str(result_text)

            # Check for API errors first
            if "Invalid model:" in result_text or "API error" in result_text:
                logger.error(f"[CONSTRAINT_MONITOR] Vibe API error: {result_text[:200]}...")
                # Don't submit healing task for API errors - this is a configuration issue
                return

            if "VIOLATION:" in result_text:
                logger.warning(f"[CONSTRAINT_MONITOR] Violation detected: {result_text[:100]}...")

                # Extract violation details - improved parsing
                violation = "Unknown Violation"
                for line in result_text.split("\n"):
                    if line.startswith("VIOLATION:"):
                        violation = line.replace("VIOLATION:", "").strip()
                        break
                    if "VIOLATION:" in line:  # Handle cases where VIOLATION: is not at start
                        parts = line.split("VIOLATION:")
                        if len(parts) > 1:
                            violation = parts[1].strip()
                            break

                # If we still have "Unknown Violation", try to extract more context
                if violation == "Unknown Violation":
                    for line in result_text.split("\n"):
                        if any(
                            keyword in line.lower()
                            for keyword in ["violation", "constraint", "error"]
                        ):
                            violation = line.strip()[:100]  # Limit length
                            break

                # Submit Priority 2 Healing Task
                await parallel_healing_manager.submit_healing_task(
                    step_id="constraint_monitor",
                    error=f"User Constraint Violation: {violation}",
                    step_context={"action": "monitor_constraints", "constraint": violation},
                    log_context=log_context,
                    priority=2,  # HIGH PRIORITY
                )

        except Exception as e:
            logger.warning(f"[CONSTRAINT_MONITOR] Check failed: {e}")
        finally:
            self._is_running = False

    def _read_constraints(self) -> list[str]:
        """Read constraints from file."""
        if not os.path.exists(CONSTRAINTS_FILE):
            return []

        try:
            with open(CONSTRAINTS_FILE) as f:
                lines = f.readlines()
            # Filter comments and empty lines
            return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
        except Exception:
            return []


constraint_monitor = ConstraintMonitor()
