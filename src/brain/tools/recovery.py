import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from src.brain.logger import logger
from src.brain.state_manager import state_manager

RECOVERY_FILE = Path(".recovery_state.json")


class RecoveryManager:
    """
    Manages state snapshots for the 'Phoenix Protocol' (Self-Healing Restart).
    Saves Redis state and Orchestrator memory to a local JSON file.
    """

    async def save_snapshot(
        self, orchestrator_state: dict[str, Any], task_context: dict[str, Any]
    ) -> bool:
        """
        Saves a full system snapshot to .recovery_state.json
        """
        try:
            logger.info("[RECOVERY] Creating system snapshot for restart...")

            # 1. Capture Redis State (if available)
            redis_dump = {}
            if state_manager and state_manager.available:
                # We save critical keys that define "current execution"
                keys_to_save = ["current_task_id", "active_plan", "session_metrics"]
                for k in keys_to_save:
                    val = await state_manager.get_key(k)
                    if val:
                        redis_dump[k] = val

            # 2. Serialize Orchestrator State
            # We need to be careful with objects that aren't JSON serializable
            # For messages, they usually have to_dict or we fallback to string
            orch_dump = {}
            for k, v in orchestrator_state.items():
                if k == "messages":
                    # Simplify messages for snapshot
                    # Full history is in DB, we just need the "last step" context if needed
                    # Actually, Orchestrator rebuilds from DB, so we mainly need the ID
                    continue
                if isinstance(v, str | int | float | bool | list | dict | type(None)):
                    orch_dump[k] = v
                else:
                    orch_dump[k] = str(v)

            snapshot = {
                "timestamp": datetime.now().isoformat(),
                "session_id": task_context.get("session_id"),
                "task_id": task_context.get("task_id"),
                "orchestrator_state": orch_dump,
                "redis_state": redis_dump,
                "resume_step_id": task_context.get("current_step_id"),
                "reason": task_context.get("reason", "Self-healing restart"),
            }

            with open(RECOVERY_FILE, "w") as f:
                json.dump(snapshot, f, indent=2)

            logger.info(f"[RECOVERY] Snapshot saved to {RECOVERY_FILE.absolute()}")
            return True

        except Exception as e:
            logger.error(f"[RECOVERY] Failed to save snapshot: {e}")
            return False

    def load_snapshot(self) -> dict[str, Any] | None:
        """
        Loads the recovery snapshot if it exists.
        Returns None if no snapshot found.
        """
        if not RECOVERY_FILE.exists():
            return None

        try:
            with open(RECOVERY_FILE) as f:
                data = json.load(f)

            logger.info(f"[RECOVERY] Found recovery snapshot from {data.get('timestamp')}")
            return data
        except Exception as e:
            logger.error(f"[RECOVERY] Failed to load snapshot: {e}")
            return None

    def clear_snapshot(self):
        """Removes the snapshot file after successful resumption"""
        if RECOVERY_FILE.exists():
            try:
                os.remove(RECOVERY_FILE)
                logger.info("[RECOVERY] Snapshot cleared.")
            except Exception as e:
                logger.error(f"[RECOVERY] Failed to clear snapshot: {e}")


# Singleton
recovery_manager = RecoveryManager()
