
"""Constraint Monitor

Periodically checks system logs against user-defined constraints.
Triggers priority parallel healing if violations are detected.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

from src.brain.config import BRAIN_DIR
from src.brain.logger import logger
from src.brain.parallel_healing import parallel_healing_manager

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
            
            self._last_check_logs = recent_logs[-20:] # Keep small history to detect duplicates

            # 3. Analyze with Vibe (using a specific tool or just prompt)
            # We'll use a fast check via Vibe prompt
            from src.brain.mcp_manager import mcp_manager
            
            # Prepare check prompt
            constraints_str = "\n".join([f"- {c}" for c in constraints])
            
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
            
            # Use 'vibe_ask' (or similar fast query)
            result = await mcp_manager.call_tool(
                "vibe",
                "vibe_prompt",
                {"prompt": prompt}
            )
            
            result_text = str(result)
            if "VIOLATION:" in result_text:
                logger.warning(f"[CONSTRAINT_MONITOR] Violation detected: {result_text[:100]}...")
                
                # Extract violation details
                violation = "Unknown Violation"
                for line in result_text.split("\n"):
                    if line.startswith("VIOLATION:"):
                        violation = line.replace("VIOLATION:", "").strip()
                        break
                
                # Submit Priority 2 Healing Task
                await parallel_healing_manager.submit_healing_task(
                    step_id="constraint_monitor",
                    error=f"User Constraint Violation: {violation}",
                    step_context={"action": "monitor_constraints", "constraint": violation},
                    log_context=log_context,
                    priority=2 # HIGH PRIORITY
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
