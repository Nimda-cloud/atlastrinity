"""AtlasTrinity State Manager

Redis-based state persistence for:
- Surviving restarts
- Checkpointing task progress
- Session recovery
"""

import json
import os
from datetime import datetime
from typing import Any

try:
    import redis.asyncio as aioredis  # type: ignore
    REDIS_AVAILABLE = True
except ImportError:
    try:
        import redis as aioredis  # type: ignore
        REDIS_AVAILABLE = True
    except ImportError:
        REDIS_AVAILABLE = False

from .logger import logger


class StateManager:
    """Manages orchestrator state persistence using Redis.

    Features:
    - Save/restore task state
    - Checkpointing during execution
    - Session recovery after restart
    """

    def __init__(self, host: str = "localhost", port: int = 6379, prefix: str = "atlastrinity"):
        from .config_loader import config

        self.prefix = prefix
        self.available = False

        if not REDIS_AVAILABLE:
            logger.warning("[STATE] Redis not installed. Running without persistence.")
            return

        # Priority: EnvVar > Config > Default Host/Port
        redis_url = os.getenv("REDIS_URL") or config.get("state.redis_url")

        if redis_url:
            self.redis_client: Any | None = aioredis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            logger.info("[STATE] Redis connected via URL")
        else:
            self.redis_client = aioredis.Redis(
                host=host,
                port=port,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            logger.info(f"[STATE] Redis connected at {host}:{port}")

        # Connection will be tested lazily or in initialize
        self.available = True

    def _key(self, name: str) -> str:
        return f"{self.prefix}:{name}"

    async def save_session(self, session_id: str, state: dict):
        """Persist session state to Redis"""
        if not self.available or self.redis_client is None:
            return
        try:
            key = self._key(f"session:{session_id}")
            # Ensure state is JSON serializable
            await self.redis_client.set(key, json.dumps(state, default=str))  # type: ignore
            # Also update last session pointer
            await self.redis_client.set(self._key("last_session"), session_id)  # type: ignore
            logger.info(f"[STATE] Session {session_id} saved")
        except Exception as e:
            logger.error(f"[STATE] Failed to save session: {e}")

    async def restore_session(self, session_id: str) -> dict | None:
        """Retrieve session state from Redis"""
        if not self.available or self.redis_client is None:
            return None
        try:
            key = self._key(f"session:{session_id}")
            data = await self.redis_client.get(key)  # type: ignore
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"[STATE] Failed to restore session: {e}")
            return None

    async def list_sessions(self) -> list[dict]:
        """List all available sessions"""
        if not self.available or self.redis_client is None:
            return []
        try:
            pattern = self._key("session:*")
            keys = await self.redis_client.keys(pattern)  # type: ignore
            sessions = []
            for k in keys:
                # Key is byte if decode_responses=False, but we set it True
                s_id = k.split(":")[-1]
                sessions.append({"id": s_id, "key": k})
            return sessions
        except Exception as e:
            logger.error(f"[STATE] Failed to list sessions: {e}")
            return []

    async def delete_session(self, session_id: str):
        """Remove a session from persistence"""
        if not self.available or self.redis_client is None:
            return
        try:
            key = self._key(f"session:{session_id}")
            await self.redis_client.delete(key)  # type: ignore
        except Exception as e:
            logger.error(f"[STATE] Failed to delete session: {e}")

    async def clear_session(self, session_id: str):
        """Alias for delete_session for compatibility"""
        await self.delete_session(session_id)

    async def checkpoint(self, session_id: str, step_id: Any, result: Any):
        """Save partial progress during a task"""
        if not self.available or self.redis_client is None:
            return
        try:
            key = self._key(f"checkpoint:{session_id}")
            checkpoint_data = {
                "last_step": step_id,
                "timestamp": datetime.now().isoformat(),
                "result": result,
            }
            await self.redis_client.set(key, json.dumps(checkpoint_data, default=str))  # type: ignore
        except Exception as e:
            logger.error(f"[STATE] Checkpoint failed: {e}")

    async def get_last_checkpoint(self, session_id: str) -> dict | None:
        """Get the last successful checkpoint for a session"""
        if not self.available or self.redis_client is None:
            return None
        try:
            key = self._key(f"checkpoint:{session_id}")
            data = await self.redis_client.get(key)  # type: ignore
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"[STATE] Failed to get checkpoint: {e}")
            return None

    async def set_current_task(self, task_id: str, metadata: dict):
        """Store info about the currently active task"""
        if not self.available or self.redis_client is None:
            return
        try:
            key = self._key("active_task")
            data = {"id": task_id, "metadata": metadata, "started": datetime.now().isoformat()}
            await self.redis_client.set(key, json.dumps(data, default=str))  # type: ignore
        except Exception as e:
            logger.error(f"[STATE] Failed to set active task: {e}")

    async def get_current_task(self) -> dict | None:
        """Get info about the currently active task"""
        if not self.available or self.redis_client is None:
            return None
        try:
            key = self._key("active_task")
            data = await self.redis_client.get(key)  # type: ignore
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"[STATE] Failed to get active task: {e}")
            return None

    async def clear_active_task(self):
        """Clear the active task flag"""
        if not self.available or self.redis_client is None:
            return
        try:
            await self.redis_client.delete(self._key("active_task"))  # type: ignore
        except Exception as e:
            logger.error(f"[STATE] Failed to clear active task: {e}")

    async def publish_event(self, channel: str, message: dict):
        """Publish a message to a Redis channel (Pub/Sub)"""
        if not self.available or self.redis_client is None:
            return
        try:
            full_channel = self._key(f"events:{channel}")
            await self.redis_client.publish(full_channel, json.dumps(message, default=str))  # type: ignore
        except Exception as e:
            logger.error(f"[STATE] Failed to publish event: {e}")


# Singleton instance
state_manager = StateManager()
