"""AtlasTrinity Orchestrator
LangGraph-based state machine that coordinates Agents (Atlas, Tetyana, Grisha)
"""

import ast
import asyncio
import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypedDict, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage  # type: ignore
from langgraph.graph import END, StateGraph

try:
    from langgraph.graph.message import add_messages
except ImportError:
    def add_messages(left: Any, right: Any) -> Any:  # type: ignore
        return left + right

from src.brain.agents import Atlas, Grisha, Tetyana
from src.brain.agents.tetyana import StepResult
from src.brain.behavior_engine import workflow_engine
from src.brain.config import IS_MACOS, PLATFORM_NAME
from src.brain.config_loader import config
from src.brain.consolidation import consolidation_module
from src.brain.context import shared_context
from src.brain.db.manager import db_manager
from src.brain.db.schema import ChatMessage, RecoveryAttempt
from src.brain.db.schema import ConversationSummary as DBConvSummary
from src.brain.db.schema import LogEntry as DBLog
from src.brain.db.schema import Session as DBSession
from src.brain.db.schema import Task as DBTask
from src.brain.db.schema import TaskStep as DBStep
from src.brain.db.schema import ToolExecution as DBToolExecution
from src.brain.error_router import error_router
from src.brain.knowledge_graph import knowledge_graph
from src.brain.logger import logger
from src.brain.mcp_manager import mcp_manager
from src.brain.message_bus import AgentMsg, MessageType, message_bus
from src.brain.metrics import metrics_collector
from src.brain.notifications import notifications
from src.brain.state_manager import state_manager
from src.brain.voice.stt import WhisperSTT
from src.brain.voice.tts import VoiceManager


class SystemState(Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    CHAT = "CHAT"


class TrinityState(TypedDict):
    messages: list[BaseMessage]
    system_state: str
    current_plan: Any | None
    step_results: list[dict[str, Any]]
    error: str | None
    logs: list[dict[str, Any]]
    session_id: str | None
    db_session_id: str | None
    db_task_id: str | None
    _theme: str | None


class Trinity:
    def __init__(self):
        self.atlas = Atlas()
        self.tetyana = Tetyana()
        self.grisha = Grisha()
        self.voice = VoiceManager()
        self.stt = WhisperSTT()

        # Ensure global singletons are loaded

        # Initialize graph
        self.graph = self._build_graph()
        self._log_lock = asyncio.Lock()
        self.current_session_id = "current_session"  # Default alias for the last active session
        self._resumption_pending = False
        self._user_node_created = False
        self.active_task = None  # Track current run task for cancellation
        self.state = {
            "messages": [],
            "system_state": SystemState.IDLE.value,
            "current_plan": None,
            "step_results": [],
            "error": None,
            "logs": [],
        }
        self._background_tasks = set()

        # ARCHITECTURAL IMPROVEMENT: Live Voice status during long tools (like Vibe)
        self._last_live_speech_time = 0
        from .mcp_manager import mcp_manager

        mcp_manager.register_log_callback(self._mcp_log_voice_callback)

    async def initialize(self):
        """Async initialization of system components via Config-Driven Workflow"""
        # Синхронізація shared_context з конфігурацією
        from src.brain.config_loader import config
        from src.brain.context import shared_context

        shared_context.sync_from_config(config.all)

        # Execute 'startup' workflow from behavior config
        # This replaces hardcoded service checks and state init
        context = {"orchestrator": self}
        success = await workflow_engine.execute_workflow("startup", context)

        if not success:
            logger.error(
                "[ORCHESTRATOR] Startup workflow failed or partial. Proceeding with caution.",
            )

        # Legacy fallback if workflow didn't fully initialize context (safety net)
        if not self.state:
            self.state = {
                "messages": [],
                "system_state": SystemState.IDLE.value,
                "current_plan": None,
                "step_results": [],
                "error": None,
                "logs": [],
            }

        # Check for pending restart state
        await self._resume_after_restart()

        # If resumption is pending, trigger the run() in background after a short delay
        if getattr(self, "_resumption_pending", False):

            async def auto_resume():
                await asyncio.sleep(5)  # Wait for all components to stabilize
                messages = self.state.get("messages", [])
                if messages:
                    # Get the original request from the first HumanMessage
                    original_request = ""
                    for m in messages:
                        if "HumanMessage" in str(type(m)) or (
                            isinstance(m, dict) and m.get("type") == "human"
                        ):
                            if hasattr(m, "content"):
                                original_request = str(m.content)
                            elif isinstance(m, dict):
                                original_request = str(m.get("content", ""))
                            else:
                                original_request = str(m)
                            break

                    if original_request:
                        logger.info(
                            f"[ORCHESTRATOR] Auto-resuming task: {original_request[:50]}...",
                        )
                        await self.run(original_request)

            asyncio.create_task(auto_resume())

        logger.info(f"[GRISHA] Auditor ready. Vision: {self.grisha.llm.model_name}")

    async def warmup(self, async_warmup: bool = True):
        """Warm up memory, voice types, and engine models."""
        try:
            logger.info("[ORCHESTRATOR] Warming up system components...")

            async def run_warmup():
                # 1. Warm up STT
                logger.info(f"[ORCHESTRATOR] Pre-loading STT model: {self.stt.model_name}...")
                model = await self.stt.get_model()
                if model:
                    logger.info("[ORCHESTRATOR] STT model loaded successfully.")
                else:
                    logger.warning("[ORCHESTRATOR] STT model unavailable.")

                # 2. Warm up TTS
                logger.info("[ORCHESTRATOR] Initializing TTS engine...")
                await self.voice.get_engine()
                logger.info("[ORCHESTRATOR] Voice engines ready.")

            if async_warmup:
                asyncio.create_task(run_warmup())
            else:
                await run_warmup()

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Warmup failed: {e}")

    async def reset_session(self):
        """Reset the current session and start a fresh one"""
        self.state = {
            "messages": [],
            "system_state": SystemState.IDLE.value,
            "current_plan": None,
            "step_results": [],
            "error": None,
            "logs": [],
        }
        # Clear IDs so they are regenerated on next run
        if "db_session_id" in self.state:
            del self.state["db_session_id"]
        if "db_task_id" in self.state:
            del self.state["db_task_id"]
        # Auto-backup before clearing session
        try:
            import sys
            from pathlib import Path

            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            try:
                from scripts import setup_dev

                await asyncio.to_thread(setup_dev.backup_databases)
            except ImportError:
                # Handle non-package scripts folder
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "setup_dev",
                    str(project_root / "scripts" / "setup_dev.py"),
                )
                if spec and spec.loader:
                    setup_dev = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(setup_dev)
                    await asyncio.to_thread(setup_dev.backup_databases)
            await self._log("📦 Backup попередньої сесії...", "system")
        except Exception as e:
            logger.warning(f"[BACKUP] Не вдалося створити backup: {e}")

        if state_manager.available:
            await state_manager.clear_session(self.current_session_id)

        # Create a new unique session ID
        self.current_session_id = f"session_{uuid.uuid4().hex[:8]}"

        await self._log(f"Нова сесія розпочата ({self.current_session_id})", "system")
        return {"status": "success", "session_id": self.current_session_id}

    async def load_session(self, session_id: str):
        """Load a specific session from Redis, or reconstruct from DB if missing"""
        if not state_manager.available:
            return {"status": "error", "message": "Persistence unavailable"}

        saved_state = await state_manager.restore_session(session_id)
        if saved_state:
            self.state = saved_state
            self.current_session_id = session_id
            await self._log(f"Сесія {session_id} відновлена з пам'яті", "system")
            return {"status": "success"}

        # Attempt DB Reconstruction
        try:
            from sqlalchemy import select

            async with await db_manager.get_session() as db_sess:
                # 1. Fetch Session Theme
                sess_info = await db_sess.execute(
                    select(DBSession).where(DBSession.id == session_id)
                )
                db_sess_obj = sess_info.scalar()
                if not db_sess_obj:
                    # Try searching by string ID in metadata or logs if UUID fails
                    # But session_id here should be the ID
                    return {"status": "error", "message": "Session not found in DB"}

                # 2. Fetch Chat History
                chat_info = await db_sess.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == str(session_id))
                    .order_by(ChatMessage.created_at.asc())
                )
                db_messages = chat_info.scalars().all()

                # Reconstruct LangChain messages
                reconstructed_messages: list[BaseMessage] = []
                for m in db_messages:
                    if m.role == "human":
                        reconstructed_messages.append(HumanMessage(content=m.content))
                    elif m.role == "ai":
                        agent = (
                            m.metadata_blob.get("agent", "ATLAS") if m.metadata_blob else "ATLAS"
                        )
                        reconstructed_messages.append(AIMessage(content=m.content, name=agent))

                # 3. Fetch Logs (Optional but nice)
                log_info = await db_sess.execute(
                    select(DBLog)
                    .where(DBLog.session_id == str(session_id))
                    .order_by(DBLog.timestamp.asc())
                )
                db_logs = log_info.scalars().all()
                reconstructed_logs = []
                for l in db_logs:
                    reconstructed_logs.append(
                        {
                            "id": f"db-log-{l.id}",
                            "timestamp": l.timestamp.timestamp(),
                            "agent": l.source.upper(),
                            "message": l.message,
                            "type": l.metadata_blob.get("type", "info")
                            if l.metadata_blob
                            else "info",
                        }
                    )

                # Initial Fresh State
                self.state = {
                    "messages": reconstructed_messages,
                    "system_state": SystemState.IDLE.value,
                    "current_plan": None,
                    "step_results": [],
                    "error": None,
                    "logs": reconstructed_logs,
                    "_theme": db_sess_obj.metadata_blob.get("theme", "Restored Session"),
                }
                self.current_session_id = session_id
                await self._log(f"Сесія {session_id} відновлена з бази даних", "system")
                return {"status": "success"}

        except Exception as e:
            logger.error(f"Failed to reconstruct session from DB: {e}")
            return {"status": "error", "message": f"DB Reconstruction failed: {e}"}

    def _build_graph(self):
        """Builds LangGraph dynamically from orchestration_flow config."""
        from src.brain.behavior_engine import behavior_engine

        flow_config = behavior_engine.config.get("orchestration_flow", {})

        workflow = StateGraph(TrinityState)  # type: ignore[arg-type]

        # Mapping of config node types to orchestrator functions
        node_functions = {
            "planner": self.planner_node,
            "executor": self.executor_node,
            "verifier": self.verifier_node,
        }

        # 1. Define nodes
        nodes = flow_config.get("nodes", [])
        for node_cfg in nodes:
            name = node_cfg.get("name")
            n_type = node_cfg.get("type")
            if isinstance(name, str) and n_type in node_functions:
                action = node_functions[n_type]
                workflow.add_node(name, action)  # type: ignore

        # 2. Define edges
        entry_point = flow_config.get("entry_point")
        if entry_point:
            workflow.set_entry_point(entry_point)

        for node_cfg in nodes:
            name = node_cfg.get("name")
            next_node = node_cfg.get("next")
            cond_edge = node_cfg.get("conditional_edge")

            if next_node:
                workflow.add_edge(name, next_node)
            elif cond_edge:
                evaluator_name = cond_edge.get("evaluator")
                mapping = cond_edge.get("mapping", {})
                # Resolve __end__ to END
                resolved_mapping = {k: (v if v != "__end__" else END) for k, v in mapping.items()}

                # Check if evaluator is a method on Trinity
                eval_func = getattr(self, evaluator_name, None) if evaluator_name else None
                if name and eval_func:
                    workflow.add_conditional_edges(name, eval_func, resolved_mapping)

        return workflow.compile()

    def _mcp_result_to_text(self, res: Any) -> str:
        if isinstance(res, dict):
            try:
                return json.dumps(res, ensure_ascii=False)
            except Exception:
                return str(res)

        if hasattr(res, "content") and isinstance(res.content, list):
            parts: list[str] = []
            for item in res.content:
                txt = getattr(item, "text", None)
                if isinstance(txt, str) and txt:
                    parts.append(txt)
            if parts:
                return "".join(parts)
        return str(res)

    def _extract_vibe_payload(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return ""
        try:
            data = json.loads(t)
        except Exception:
            try:
                data = ast.literal_eval(t)
            except Exception:
                return t

        if isinstance(data, dict):
            stdout = data.get("stdout")
            stderr = data.get("stderr")
            if isinstance(stdout, str) and stdout.strip():
                return stdout.strip()
            if isinstance(stderr, str) and stderr.strip():
                return stderr.strip()
        return t

    def stop(self):
        """Immediately stop voice and cancel current orchestration task"""
        logger.info("[TRINITY] 🛑 STOP SIGNAL RECEIVED.")
        self.voice.stop()
        if self.active_task and not self.active_task.done():
            logger.info("[TRINITY] Cancelling active orchestration task.")
            self.active_task.cancel()
        self.state["system_state"] = SystemState.IDLE.value

    async def _speak(self, agent_id: str, text: str):
        """Voice wrapper with config-driven sanitization"""
        from src.brain.behavior_engine import behavior_engine

        voice_config = behavior_engine.get_output_processing("voice")

        # 1. Clean up text for TTS using config rules
        import re

        processed_text = text
        for rule in voice_config.get("sanitization_rules", []):
            pattern = rule.get("pattern")
            replacement = rule.get("replacement", "")
            if pattern:
                processed_text = re.sub(pattern, replacement, processed_text)

        processed_text = processed_text.strip()

        # If text is empty or outside length limits, skip
        min_len = voice_config.get("min_length", 2)
        max_len = voice_config.get("max_length", 5000)
        if not processed_text or len(processed_text) < min_len or len(processed_text) > max_len:
            return

        # 2. Prepare text via TTS engine (Sanitize + Translate if needed)
        # This ensures Chat and Voice are 100% synchronized
        final_text = await self.voice.prepare_speech_text(processed_text)
        if not final_text:
            return

        print(f"[{agent_id.upper()}] Speaking: {final_text}")

        # 3. Synchronize with UI chat log
        if hasattr(self, "state") and self.state is not None:
            if "messages" not in self.state:
                self.state["messages"] = []

            # Avoid duplicate messages if this was already in the history (e.g. during resumption)
            # We only append if it's the latest message (real-time generated)
            self.state["messages"].append(AIMessage(content=final_text, name=agent_id.upper()))
            asyncio.create_task(self._save_chat_message("ai", final_text, agent_id))

        await self._log(final_text, source=agent_id, type="voice")
        try:
            # Pass PREPARED text to voice
            await self.voice.speak(agent_id, final_text)
        except asyncio.CancelledError:
            # Re-raise to allow the task cancellation to proceed
            raise
        except Exception as e:
            print(f"TTS Error: {e}")

    async def _mcp_log_voice_callback(self, msg: str, server_name: str, level: str):
        """Callback to handle live log notifications from MCP servers for voice feedback."""
        import time

        now = time.time()

        # Rate limit live speech to once per 10 seconds to avoid spamming
        if now - self._last_live_speech_time < 10:
            return

        # We specifically care about Vibe-Live updates
        significant_markers = ["[VIBE-THOUGHT]", "[VIBE-ACTION]", "[VIBE-LIVE]"]
        if server_name == "vibe" and any(marker in msg for marker in significant_markers):
            # Strip markers for speech
            speech_text = msg
            for marker in significant_markers:
                speech_text = speech_text.replace(marker, "")

            # Remove emojis
            import re

            speech_text = re.sub(r"[^\w\s\.,!\?]", "", speech_text).strip()

            if len(speech_text) > 5:
                # Use 'atlas' for status updates
                self._last_live_speech_time = int(now)
                asyncio.create_task(self._speak("atlas", speech_text))

    async def _log(self, text: str, source: str = "system", type: str = "info"):
        """Log wrapper with message types and DB persistence"""
        # Ensure text is a string to prevent React "Objects are not valid as a React child" error
        text_str = str(text)
        logger.info(f"[{source.upper()}] {text_str}")

        # DB Persistence
        if db_manager.available:
            async with self._log_lock:
                try:
                    async with await db_manager.get_session() as session:
                        entry = DBLog(
                            session_id=self.current_session_id,
                            level=type.upper(),
                            source=source,
                            message=text_str,
                            metadata_blob={"type": type},
                        )
                        session.add(entry)
                        await session.commit()
                except Exception as e:
                    logger.error(f"DB Log failed: {e}")

        if self.state:
            # Basic log format for API
            import time

            log_entry = {
                "id": f"log-{len(self.state.get('logs') or [])}-{time.time()}",
                "timestamp": time.time(),
                "agent": source.upper(),
                "message": text_str,
                "type": type,
            }
            if "logs" not in self.state:
                self.state["logs"] = []
            self.state["logs"].append(log_entry)

            # 3. Publish to Redis for real-time UI updates
            if state_manager.available:
                try:
                    asyncio.create_task(state_manager.publish_event("logs", log_entry))
                except Exception as e:
                    logger.warning(f"Failed to publish log to Redis: {e}")

    async def _save_chat_message(self, role: str, content: str, agent_id: str | None = None):
        """Persist a chat message to the DB for history reconstruction"""
        if not db_manager.available or not self.current_session_id:
            return

        try:
            async with await db_manager.get_session() as session:
                msg = ChatMessage(
                    session_id=self.current_session_id,
                    role=role,
                    content=str(content),
                    metadata_blob={"agent": agent_id.upper() if agent_id else None},
                )
                session.add(msg)
                await session.commit()
        except Exception as e:
            logger.error(f"[DB] ChatMessage storage failed: {e}")

    async def _resume_after_restart(self):
        """Check if we are recovering from a restart and resume state"""
        if not state_manager.available:
            return

        try:
            # Check for restart flag in Redis
            restart_key = state_manager._key("restart_pending")
            data = None
            if state_manager.redis_client:
                data = await state_manager.redis_client.get(restart_key)

            if data:
                restart_info = json.loads(cast("str", data))
                reason = restart_info.get("reason", "Unknown reason")
                session_id = restart_info.get("session_id", "current_session")

                logger.info(
                    f"[ORCHESTRATOR] Recovering from self-healing restart. Reason: {reason}",
                )

                if session_id == "current":
                    # Use the most recent session from list_sessions
                    sessions = await state_manager.list_sessions()
                    if sessions:
                        session_id = sessions[0]["id"]

                saved_state = await state_manager.restore_session(session_id)
                if saved_state:
                    self.state = saved_state
                    self.current_session_id = session_id

                    # Clear the flag
                    if state_manager.redis_client:
                        await state_manager.redis_client.delete(restart_key)
                    self._resumption_pending = True

                    await self._log(
                        f"Система успішно перезавантажилася та відновила стан. Причина: {reason}",
                        "system",
                    )
                    await self._speak(
                        "atlas",
                        "Я повернувся. Продовжую виконання завдання з того ж місця.",
                    )
        except Exception as e:
            logger.error(f"Failed to resume after restart: {e}")

            # Implementation: querying Redis for a specific "system:restart_pending" key
            # which we would have set in tool_dispatcher (we need to update tool_dispatcher to set this!)
            # WAIT: tool_dispatcher doesn't have access to state_manager directly usually.
            # We should probably update tool_dispatcher to use state_manager if available.

            # ALTERNATIVE: orchestrator handles the restart tool?
            # No, dispatcher handles it. Dispatcher needs access to state_manager to set the flag.

            # For now, let's just log that we are booting up.
            await self._log("System booted. Checking for pending tasks...", "system")

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Resume check failed: {e}")

    async def _update_task_metadata(self):
        """Оновлює metadata_blob в Task для збереження поточного рекурсивного контексту."""
        try:
            from sqlalchemy import update

            from src.brain.context import shared_context
            from src.brain.db.manager import db_manager

            if (
                not db_manager
                or not getattr(db_manager, "available", False)
                or not self.state.get("db_task_id")
            ):
                return

            task_metadata = {
                "goal_stack": shared_context.goal_stack.copy(),
                "parent_goal": shared_context.parent_goal,
                "recursive_depth": shared_context.recursive_depth,
                "current_goal": shared_context.current_goal,
            }

            async with await db_manager.get_session() as db_sess:
                await db_sess.execute(
                    update(DBTask)
                    .where(DBTask.id == self.state["db_task_id"])
                    .values(metadata_blob=task_metadata)
                )
                await db_sess.commit()

        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Failed to update task metadata: {e}")

    async def _verify_db_ids(self):
        """Verify that restored DB IDs exist. If not, clear them."""
        try:
            from src.brain.db.manager import db_manager

            if not db_manager or not getattr(db_manager, "available", False):
                return
        except (ImportError, NameError):
            return

        session_id_str = self.state.get("db_session_id")
        task_id_str = self.state.get("db_task_id")

        async with await db_manager.get_session() as db_sess:
            import uuid

            from sqlalchemy import select

            if session_id_str and isinstance(session_id_str, str):
                try:
                    session_id = uuid.UUID(session_id_str)
                    result = await db_sess.execute(
                        select(DBSession).where(DBSession.id == session_id),
                    )
                    if not result.scalar():
                        logger.warning(
                            f"[ORCHESTRATOR] Restored session_id {session_id_str} not found in DB. Clearing.",
                        )
                        del self.state["db_session_id"]
                        if "db_task_id" in self.state:
                            del self.state["db_task_id"]
                        return  # If session is gone, task is definitely gone
                except Exception as e:
                    logger.error(f"Error verifying session_id {session_id_str}: {e}")
                    # If it's not a valid UUID, it's definitely stale/junk
                    del self.state["db_session_id"]

            if task_id_str and isinstance(task_id_str, str):
                try:
                    task_id = uuid.UUID(task_id_str)
                    result = await db_sess.execute(select(DBTask).where(DBTask.id == task_id))
                    if not result.scalar():
                        logger.warning(
                            f"[ORCHESTRATOR] Restored task_id {task_id_str} not found in DB. Clearing.",
                        )
                        del self.state["db_task_id"]
                except Exception as e:
                    logger.error(f"Error verifying task_id {task_id_str}: {e}")
                    del self.state["db_task_id"]

    def get_state(self) -> dict[str, Any]:
        """Return current system state for API"""
        if not hasattr(self, "state") or not self.state:
            logger.warning("[ORCHESTRATOR] State not initialized, returning default state")
            return {
                "system_state": SystemState.IDLE.value,
                "current_task": "Waiting for input...",
                "active_agent": "ATLAS",
                "logs": [],
                "step_results": [],
            }

        # Determine active agent based on system state
        active_agent = "ATLAS"
        sys_state = self.state.get("system_state", SystemState.IDLE.value)

        if sys_state == SystemState.EXECUTING.value:
            active_agent = "TETYANA"
        elif sys_state == SystemState.VERIFYING.value:
            active_agent = "GRISHA"

        plan = self.state.get("current_plan")

        # Handle plan being either object or string (from Redis/JSON serialization)
        if plan:
            if isinstance(plan, str):
                task_summary = plan
            elif hasattr(plan, "goal"):
                task_summary = plan.goal
            else:
                task_summary = str(plan)
        else:
            task_summary = "IDLE"

        # Prepare messages for frontend
        messages = []
        from datetime import datetime

        msg_list = self.state.get("messages")
        if isinstance(msg_list, list):
            for m in msg_list:
                if isinstance(m, HumanMessage):
                    messages.append(
                        {
                            "agent": "USER",
                            "text": m.content,
                            "timestamp": datetime.now().timestamp(),
                            "type": "text",
                        },
                    )
                elif isinstance(m, AIMessage):
                    # Support custom agent names (e.g. TETYANA, GRISHA) stored in .name
                    agent_name = m.name if hasattr(m, "name") and m.name else "ATLAS"
                    messages.append(
                        {
                            "agent": agent_name,
                            "text": m.content,
                            "timestamp": datetime.now().timestamp(),
                            "type": "voice",
                        },
                    )

        return {
            "system_state": sys_state,
            "current_task": task_summary,
            "active_agent": active_agent,
            "session_id": self.current_session_id,
            "messages": messages[-50:],
            "logs": (self.state.get("logs") or [])[-100:],
            "step_results": self.state.get("step_results") or [],
            "metrics": metrics_collector.get_metrics(),
        }

    async def _planning_loop(self, analysis, user_request, is_subtask, history):
        """Handle the planning and verification loop."""
        max_retries = 1
        plan = None
        
        async def keep_alive_logging():
            import time
            while True:
                await asyncio.sleep(15)
                await self._log("Atlas is thinking... (Planning logic flow)", "system")

        for attempt in range(max_retries + 1):
            if attempt > 0:
                await self._log(f"🔄 Спроба перепланування {attempt}/{max_retries}...", "system")
                analysis["simulation_result"] = getattr(self, "_last_verification_report", None)
                analysis["failed_plan"] = plan

            planning_task = asyncio.create_task(self.atlas.create_plan(analysis))
            logger_task = asyncio.create_task(keep_alive_logging())
            try:
                plan = await asyncio.wait_for(
                    planning_task,
                    timeout=config.get("orchestrator", {}).get("task_timeout", 1200.0),
                )
            finally:
                logger_task.cancel()

            if not plan or not plan.steps:
                await self._handle_no_steps_plan(user_request, history)
                return None

            self.state["current_plan"] = plan

            if not is_subtask:
                verified_plan = await self._verify_plan_with_grisha(plan, user_request, attempt, max_retries)
                if verified_plan:
                    plan = verified_plan
                    break
                elif attempt < max_retries:
                    continue
                else:
                    break
            break
        return plan

    async def _handle_no_steps_plan(self, user_request, history):
        """Handle case where Atlas generates no steps."""
        msg = self.atlas.get_voice_message("no_steps")
        await self._speak("atlas", msg)
        fallback_chat = await self.atlas.chat(user_request, history=history, use_deep_persona=True)
        await self._speak("atlas", fallback_chat)

    async def _verify_plan_with_grisha(self, plan, user_request, attempt, max_retries):
        """Verify plan using Grisha and handle rejections."""
        self.state["system_state"] = SystemState.VERIFYING.value
        try:
            res = await self.grisha.verify_plan(plan, user_request, fix_if_rejected=(attempt >= 1))
            self._last_verification_report = res.description
            
            if res.verified:
                await self._speak("grisha", "План перевірено і затверджено. Починаємо.")
                return plan

            prefix = "Гріша знову виявив недоліки: " if attempt > 0 else "Гріша відхилив початковий план: "
            issues = "; ".join(res.issues) if res.issues else "Невідома причина"
            await self._speak("grisha", res.voice_message or f"{prefix}{issues}")
            
            if attempt >= max_retries and res.fixed_plan:
                await self._speak("grisha", "Я переписав план самостійно.")
                return res.fixed_plan
            
            if attempt == max_retries:
                logger.warning("[ORCHESTRATOR] Planning failed. FORCE PROCEED.")
                await self._speak("grisha", "План має недоліки, але ми починаємо за наказом.")
                return plan
            return None
        finally:
            self.state["system_state"] = SystemState.PLANNING.value

    async def _create_db_task(self, user_request, plan):
        """Create DB task and knowledge graph node."""
        try:
            from src.brain.db.manager import db_manager
            if not (db_manager and getattr(db_manager, "available", False) and self.state.get("db_session_id")):
                return

            async with await db_manager.get_session() as db_sess:
                new_task = DBTask(
                    session_id=self.state["db_session_id"],
                    goal=user_request,
                    status="PENDING",
                    metadata_blob={
                        "goal_stack": shared_context.goal_stack.copy(),
                        "parent_goal": shared_context.parent_goal,
                        "recursive_depth": shared_context.recursive_depth,
                    },
                    parent_task_id=self.state.get("parent_task_id"),
                )
                db_sess.add(new_task)
                await db_sess.commit()
                self.state["db_task_id"] = str(new_task.id)

                await knowledge_graph.add_node(
                    node_type="TASK",
                    node_id=f"task:{new_task.id}",
                    attributes={"goal": user_request, "steps_count": len(plan.steps)}
                )
        except Exception as e:
            logger.error(f"DB Task creation failed: {e}")

    async def run(self, user_request: str) -> dict[str, Any]:
        """Main orchestration loop with advanced persistence and memory"""
        from src.brain.context import shared_context
        self.stop()
        self.active_task = asyncio.current_task()
        start_time = asyncio.get_event_loop().time()
        session_id = self.current_session_id

        if not IS_MACOS:
            await self._log(f"WARNING: Running on {PLATFORM_NAME}.", "system", type="warning")

        is_subtask = getattr(self, "_in_subtask", False)
        if not is_subtask:
            if not hasattr(self, "state") or self.state is None:
                self.state = {"messages": [], "system_state": SystemState.IDLE.value, "current_plan": None, "step_results": [], "error": None, "logs": []}

            try:
                from src.brain.state_manager import state_manager
                if state_manager and getattr(state_manager, "available", False) and not self.state["messages"] and session_id == "current_session":
                    saved_state = await state_manager.restore_session(session_id)
                    if saved_state:
                        self.state = saved_state
            except Exception:
                pass

            if session_id == "current_session" and isinstance(self.state.get("session_id"), str):
                session_id = self.state["session_id"]
                self.current_session_id = session_id
            else:
                self.state["session_id"] = session_id

            if not self.state.get("_theme"):
                self.state["_theme"] = user_request[:40] + ("..." if len(user_request) > 40 else "")

            await self._verify_db_ids()
            self.state["messages"].append(HumanMessage(content=user_request))
            asyncio.create_task(self._save_chat_message("human", user_request))

            # DB Session
            try:
                from src.brain.db.manager import db_manager
                if db_manager and getattr(db_manager, "available", False) and "db_session_id" not in self.state:
                    async with await db_manager.get_session() as db_sess:
                        new_session = DBSession(started_at=datetime.now(UTC), metadata_blob={"theme": self.state["_theme"]})
                        db_sess.add(new_session)
                        await db_sess.commit()
                        self.state["db_session_id"] = str(new_session.id)
            except Exception:
                pass

        shared_context.push_goal(user_request)
        plan = None
        if self.state.get("current_plan") and getattr(self, "_resumption_pending", False):
            plan_obj = self.state["current_plan"]
            if isinstance(plan_obj, dict):
                from src.brain.agents.atlas import TaskPlan
                plan = TaskPlan(id=plan_obj.get("id", "resumed"), goal=plan_obj.get("goal", user_request), steps=plan_obj.get("steps", []))
            else:
                plan = plan_obj
            self._resumption_pending = False
        else:
            try:
                messages_raw = self.state.get("messages", [])
                if not isinstance(messages_raw, list):
                    messages_raw = []
                history: list[Any] = messages_raw[-25:-1] if len(messages_raw) > 1 else []
                analysis = await self.atlas.analyze_request(user_request, history=history)
                intent = analysis.get("intent")

                from src.brain.behavior_engine import behavior_engine
                if intent and intent in behavior_engine.config.get("workflows", {}):
                    self.state["system_state"] = SystemState.EXECUTING.value
                    success = await workflow_engine.execute_workflow(str(intent), {"orchestrator": self, "user_request": user_request, "intent_analysis": analysis})
                    msg = f"Workflow '{intent}' completed." if success else f"Workflow '{intent}' failed."
                    await self._speak("atlas", msg)
                    self.active_task = None
                    return {"status": "completed", "result": msg, "type": "workflow"}

                if intent in ["chat", "recall", "status", "solo_task"]:
                    response = analysis.get("initial_response") or await self.atlas.chat(user_request, history=history, use_deep_persona=analysis.get("use_deep_persona", False), intent=intent, on_preamble=self._speak)
                    if response != "__ESCALATE__":
                        await self._speak("atlas", response)
                        self.state["system_state"] = SystemState.IDLE.value
                        self.active_task = None
                        return {"status": "completed", "result": response, "type": intent}

                self.state["system_state"] = SystemState.PLANNING.value
                shared_context.available_mcp_catalog = await mcp_manager.get_mcp_catalog()
                await self._speak("atlas", analysis.get("voice_response") or "Аналізую запит...")

                plan = await self._planning_loop(analysis, user_request, is_subtask, history)
                if not plan:
                    return {"status": "completed", "result": "No plan.", "type": "chat"}

                await self._create_db_task(user_request, plan)
                await self._speak("atlas", self.atlas.get_voice_message("plan_created", steps=len(plan.steps)))

            except Exception as e:
                logger.error(f"[ORCHESTRATOR] Planning error: {e}")
                self.state["system_state"] = SystemState.ERROR.value
                self.active_task = None
                return {"status": "error", "error": str(e)}

        self.state["system_state"] = SystemState.EXECUTING.value
        try:
            if plan and plan.steps:
                await self._execute_steps_recursive(plan.steps)
        except Exception as e:
            await self._log(f"Execution error: {e}", "error")
            self.active_task = None
            return {"status": "error", "error": str(e)}

        msgs = self.state.get("messages", [])
        msg_count = len(msgs) if isinstance(msgs, list) else 0
        await self._handle_post_execution_phase(user_request, is_subtask, start_time, session_id, msg_count)
        self.active_task = None
        return {"status": "completed", "result": self.state["step_results"]}

    async def _handle_post_execution_phase(self, user_request, is_subtask, start_time, session_id, msg_count):
        """Evaluation, memory management and cleanup."""
        duration = asyncio.get_event_loop().time() - start_time
        notifications.show_completion(user_request, True, duration)

        if not is_subtask and self.state["system_state"] != SystemState.ERROR.value:
            await self._evaluate_and_remember(user_request)

        # Final cleanup tasks
        self.state["system_state"] = SystemState.COMPLETED.value
        shared_context.pop_goal()
        
        # Async tasks for summary and background operations
        if not is_subtask and msg_count > 2:
            asyncio.create_task(self._persist_session_summary(session_id))
        
        await self._notify_task_finished(session_id)
        self._trigger_backups()

    async def _evaluate_and_remember(self, user_request):
        """Evaluate execution quality and save to LTM."""
        try:
            evaluation = await self.atlas.evaluate_execution(user_request, self.state["step_results"])
            
            if evaluation.get("achieved"):
                msg = evaluation.get("final_report") or "Завдання успішно виконано."
                await self._speak("atlas", msg)

            if evaluation.get("should_remember") and evaluation.get("quality_score", 0) >= 0.7:
                await self._save_to_ltm(user_request, evaluation)
                
            # Update DB Task
            if self.state.get("db_task_id"):
                await self._mark_db_golden_path()
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")

    async def _save_to_ltm(self, user_request, evaluation):
        """Save successful strategy to Long-term Memory."""
        from src.brain.memory import long_term_memory
        if long_term_memory and getattr(long_term_memory, "available", False):
            steps = evaluation.get("compressed_strategy") or self._extract_golden_path(self.state["step_results"])
            long_term_memory.remember_strategy(task=user_request, plan_steps=steps, outcome="SUCCESS", success=True)

    async def _mark_db_golden_path(self):
        """Mark task as golden path in DB."""
        from sqlalchemy import update

        from src.brain.db.manager import db_manager
        async with await db_manager.get_session() as db_sess:
            await db_sess.execute(update(DBTask).where(DBTask.id == self.state["db_task_id"]).values(golden_path=True))
            await db_sess.commit()

    async def _notify_task_finished(self, session_id):
        """Publish task finish event."""
        try:
            from src.brain.state_manager import state_manager
            if state_manager and getattr(state_manager, "available", False):
                await state_manager.publish_event("tasks", {"type": "task_finished", "status": "completed", "session_id": session_id})
        except Exception:
            pass

    def _trigger_backups(self):
        """Trigger background database backups."""
        try:
            from scripts.setup_dev import backup_databases
            asyncio.create_task(asyncio.to_thread(backup_databases))
        except Exception:
            pass

    async def _persist_session_summary(self, session_id: str):
        """Generates a professional summary and stores it in DB and Vector memory."""
        try:
            messages = self.state.get("messages")
            if not isinstance(messages, list) or not messages:
                return

            summary_data = await self.atlas.summarize_session(messages)
            summary = summary_data.get("summary", "No summary generated")
            entities = summary_data.get("entities", [])

            # A. Store in Vector Memory (ChromaDB)
            try:
                from src.brain.memory import long_term_memory

                if long_term_memory and getattr(long_term_memory, "available", False):
                    long_term_memory.remember_conversation(
                        session_id=session_id,
                        summary=summary,
                        metadata={"entities": entities},
                    )
            except (ImportError, NameError):
                pass

            # B. Store in Structured DB (SQLite)
            try:
                from src.brain.db.manager import db_manager

                if db_manager and getattr(db_manager, "available", False):
                    async with await db_manager.get_session() as db_sess:
                        new_summary = DBConvSummary(
                            session_id=session_id,
                            summary=summary,
                            key_entities=entities,
                        )
                        db_sess.add(new_summary)
                        await db_sess.commit()
            except Exception as e:
                logger.error(f"Failed to store summary in DB: {e}")

            # C. Add entities to Knowledge Graph
            for ent_name in entities:
                await knowledge_graph.add_node(
                    node_type="CONCEPT",
                    node_id=f"concept:{ent_name.lower().replace(' ', '_')}",
                    attributes={
                        "description": f"Entity mentioned in session {session_id}",
                        "source": "session_summary",
                    },
                    namespace="global",  # Concepts from summaries are often global-worthy, or could stay in session?
                    # For now, let's keep session concepts in global as "anchors" or maybe we decide later.
                )

            logger.info(f"[ORCHESTRATOR] Persisted professional session summary for {session_id}")

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Failed to persist session summary: {e}")

    def _extract_golden_path(self, raw_results: list[dict[str, Any]]) -> list[str]:
        """Extracts only the successful actions that led to the solution.
        Smartly filters out:
        - Failed attempts
        - Steps replaced by recovery actions
        - Repair loops (e.g. Step 3 failed -> 3.1 fixed -> Step 3 success)
        """
        golden_path = []

        # 1. Deduplicate by step_id, keeping only the LATEST attempt
        # This handles retries automatically (Attempt 1 fail, Attempt 2 success -> keeps Attempt 2)
        latest_results = {}
        for res in raw_results:
            step_id = res.get("step_id")
            latest_results[step_id] = res

        # 2. Sort by step ID to respect execution order
        # We need a robust sort for "1", "2", "2.1", "2.2", "3"
        def parse_step_id(sid):
            try:
                return [int(p) for p in str(sid).split(".")]
            except:
                return [float("inf")]  # Put weird IDs at current level end

        sorted_steps = sorted(
            latest_results.values(),
            key=lambda x: parse_step_id(x.get("step_id", "0")),
        )

        # 3. Filter for SUCCESS only
        # If a step failed but the task continued, it means it was critical to fix it?
        # No, if it failed and we moved on, usually means recovery handled it.
        # We want to capture the recovery steps (e.g. 2.1) if they succeeded.

        for item in sorted_steps:
            if item.get("success"):
                # Clean up action text
                action = item.get("action", "")

                # Remove ID prefix if present for cleaner reading e.g. "[3.1] Fix code" -> "Fix code"
                if action.startswith("[") and "]" in action:
                    try:
                        action = action.split("]", 1)[1].strip()
                    except:
                        pass

                if not action:
                    action = str(item.get("result", ""))[:100]

                golden_path.append(action)

        return golden_path

    async def _self_heal(
        self,
        step: dict[str, Any],
        step_id: str,
        error: str,
        step_result: StepResult | None,
        depth: int,
    ) -> tuple[bool, StepResult | None]:
        """
        Explicit self-healing workflow following the 8-phase protocol.

        Phases:
        1. Error Detection & Classification (already done by caller)
        2. Context Building
        3. Error Analysis & Fix Generation (Vibe)
        4. Apply Fix (Vibe auto-approve)
        5. Verification (Tests/Linters)
        6. Diagram Update (devtools MCP)
        7. Grisha Verification
        8. Auto-Commit (if enabled)

        Returns:
            (success, updated_step_result)
        """
        success = False
        updated_result = None
        recovery_attempt_id = None
        db_step_id = self.state.get("db_step_id")  # Assuming set in execute_node

        # --- Phase 2: Context Building ---
        recent_logs = []
        if self.state and "logs" in self.state:
            recent_logs = [
                f"[{l.get('agent', 'SYS')}] {l.get('message', '')}"
                for l in self.state["logs"][-20:]
            ]
        log_context = "\n".join(recent_logs)
        error_context = f"Step ID: {step_id}\nAction: {step.get('action', '')}\n"

        # Build structured recovery history
        raw_results = self.state.get("step_results", []) if self.state else []
        if not isinstance(raw_results, list):
            raw_results = []

        step_recovery_history = [
            {
                "attempt": i + 1,
                "action": str(r.get("action", ""))[:200],
                "status": "success" if r.get("success") else "failed",
                "error": str(r.get("error", ""))[:500] if r.get("error") else None,
            }
            for i, r in enumerate(raw_results)
            if isinstance(r, dict)
            and str(r.get("step_id", "")).startswith(str(step_id).split(".")[0])
        ]

        # DB: Track Recovery Attempt Start
        try:
            if db_manager and getattr(db_manager, "available", False) and db_step_id:
                async with await db_manager.get_session() as db_sess:
                    rec_attempt = RecoveryAttempt(
                        step_id=db_step_id,
                        depth=depth,
                        recovery_method="vibe",
                        success=False,
                        error_before=str(error)[:5000],
                    )
                    db_sess.add(rec_attempt)
                    await db_sess.commit()
                    recovery_attempt_id = rec_attempt.id
        except Exception as e:
            logger.error(f"Failed to log recovery attempt start: {e}")

        # --- Phase 3 & 4: Vibe Diagnosis and Fix ---
        vibe_text = None
        
        try:
            await self._log("[VIBE] Diagnostic Phase...", "vibe")
            
            # Call Vibe to analyze and propose fix (but separate execution for audit)
            vibe_res = await asyncio.wait_for(
                mcp_manager.call_tool(
                    "vibe",
                    "vibe_analyze_error",
                    {
                        "error_message": f"{error_context}\n{error}",
                        "log_context": log_context,
                        "auto_fix": False,  # We will apply fix after audit
                        "step_action": step.get("action", ""),
                        "expected_result": step.get("expected_result", ""),
                        "actual_result": str(
                            step_result.result if step_result else "N/A"
                        )[:2000],
                        "recovery_history": step_recovery_history,
                        "full_plan_context": str(self.state.get("current_plan", ""))[:3000],
                    },
                ),
                timeout=300,
            )
            vibe_text = self._extract_vibe_payload(self._mcp_result_to_text(vibe_res))

            if vibe_text:
                # --- Phase 7 (Early): Grisha Verification of PLAN ---
                # Track rejection cycles to prevent infinite loops
                # Access _rejection_cycles from self (orchestrator)
                rejection_count = getattr(self, "_rejection_cycles", {}).get(step_id, 0)

                grisha_audit = await self.grisha.audit_vibe_fix(str(error), vibe_text)

                if grisha_audit.get("audit_verdict") == "REJECT":
                    rejection_count += 1
                    if not hasattr(self, "_rejection_cycles"):
                        self._rejection_cycles = {}
                    self._rejection_cycles[step_id] = rejection_count

                    # Limit rejection cycles to 3
                    if rejection_count >= 3:
                        logger.warning(
                            f"[ORCHESTRATOR] Grisha rejected Vibe fix {rejection_count} times for step {step_id}. Escalating."
                        )
                        await self._log(
                            f"⚠️ Система застрягла після {rejection_count} відхилень Grisha. Потрібне втручання.",
                            "error",
                        )
                        # DB Update: Failure
                        if recovery_attempt_id:
                             try:
                                async with await db_manager.get_session() as db_sess:
                                    rec = await db_sess.get(RecoveryAttempt, recovery_attempt_id)
                                    if rec:
                                        rec.success = False
                                        rec.vibe_text = f"REJECTED BY GRISHA: {grisha_audit.get('reasoning')}"
                                        await db_sess.commit()
                             except Exception:
                                 pass

                        return False, StepResult(
                            step_id=step_id,
                            success=False,
                            error="need_user_input",
                            result=f"Grisha returned rejection: {grisha_audit.get('reasoning')}",
                        )

                    return False, None

                elif hasattr(self, "_rejection_cycles") and step_id in self._rejection_cycles:
                    del self._rejection_cycles[step_id]

                # Evaluate strategy via Atlas (Voice + High-level decision)
                healing_decision = await self.atlas.evaluate_healing_strategy(
                    str(error),
                    vibe_text,
                    grisha_audit,
                )
                await self._speak(
                    "atlas",
                    healing_decision.get("voice_message", "Я знайшов рішення."),
                )

                if healing_decision.get("decision") == "PROCEED":
                    # --- Phase 4: Apply Fix ---
                    
                    instructions = healing_decision.get("instructions_for_vibe", "")
                    if not instructions:
                        instructions = "Apply the fix proposed in the analysis."
                    
                    # USE SEQUENTIAL THINKING BEFORE APPLYING FIX (User Requirement)
                    await self._log(
                        "[ORCHESTRATOR] Engaging Deep Reasoning (seq_think) before applying fix...",
                        "system",
                    )
                    analysis = await self.atlas.use_sequential_thinking(
                         f"Analyze why step {step_id} failed and how to apply the vibe fix effectively.\nError: {error}\nVibe Fix: {vibe_text}\nInstructions: {instructions}",
                         total_thoughts=3,
                    )
                    if analysis.get("success"):
                        logger.info(f"[ORCHESTRATOR] Deep reasoning completed: {analysis.get('analysis', '')[:200]}...")
                    
                    await mcp_manager.call_tool(
                        "vibe",
                        "vibe_prompt",
                        {
                            "prompt": f"EXECUTE FIX: {instructions}",
                            "auto_approve": True,
                        },
                    )
                    logger.info(f"[ORCHESTRATOR] Vibe healing applied for {step_id}")
                    
                    success = True
                    # Vibe prompt tool returns dict, we assume success if no exception raised
                    
                    # --- Phase 6: Diagram Update (After successful fix) ---
                    diagram_update_enabled = config.get("self_healing", {}).get(
                        "vibe_debugging", {}
                    ).get("diagram_access", {}).get("update_after_fix", False)

                    if diagram_update_enabled:
                        try:
                            # Attempt to update diagrams if configured
                            diagram_result = await mcp_manager.call_tool(
                                "devtools",
                                "devtools_update_architecture_diagrams",
                                {
                                    "project_path": None,  # AtlasTrinity internal
                                    "commits_back": 1,
                                    "target_mode": "internal",
                                    "use_reasoning": True,
                                },
                            )
                            if diagram_result:
                                await self._log(
                                    "[SELF-HEAL] Architecture diagrams updated after fix",
                                    "system",
                                )
                        except Exception as de:
                            logger.warning(f"Diagram update after self-heal failed: {de}")

                    # DB Update: Success
                    if recovery_attempt_id:
                         try:
                            async with await db_manager.get_session() as db_sess:
                                rec = await db_sess.get(RecoveryAttempt, recovery_attempt_id)
                                if rec:
                                    rec.success = True
                                    rec.vibe_text = str(vibe_text)[:5000]
                                    await db_sess.commit()
                         except Exception:
                             pass

        except Exception as ve:
            logger.warning(f"Vibe self-healing workflow failed: {ve}")
            success = False
            if recovery_attempt_id:
                 try:
                    async with await db_manager.get_session() as db_sess:
                        rec = await db_sess.get(RecoveryAttempt, recovery_attempt_id)
                        if rec:
                            rec.success = False
                            rec.vibe_text = f"CRASH: {ve!s}"
                            await db_sess.commit()
                 except Exception:
                     pass

        return success, updated_result

    async def _execute_steps_recursive(
        self,
        steps: list[dict[str, Any]],
        parent_prefix: str | None = None,
        depth: int = 0,
    ) -> bool:
        """Recursively execute steps with proper goal context management.

        IMPORTANT: This function manages the goal stack:
        - push_goal at the START (entering sub-task)
        - pop_goal at the END (leaving sub-task)
        - Each recursive level represents a goal in the hierarchy

        Supports hierarchical numbering (e.g. 3.1, 3.2) and deep recovery.
        """
        MAX_RECURSION_DEPTH = 5
        BACKOFF_BASE_MS = 500  # Exponential backoff between depths

        if depth > MAX_RECURSION_DEPTH:
            raise RecursionError("Max task recursion depth reached. Failing task.")

        # Exponential backoff on deeper recursion to prevent overwhelming the system
        if depth > 1:
            backoff_ms = BACKOFF_BASE_MS * (2 ** (depth - 1))
            await self._log(
                f"Recursion depth {depth}: applying {backoff_ms}ms backoff",
                "orchestrator",
            )
            await asyncio.sleep(backoff_ms / 1000)

        # Track recursion metrics for analytics
        metrics_collector.record("recursion_depth", depth, tags={"parent": parent_prefix or "root"})

        # PUSH GOAL: Входимо в під-завдання (рекурсивний рівень)
        # Визначити ціль для цього рівня рекурсії
        from src.brain.context import shared_context

        goal_pushed = False
        if parent_prefix:
            # Це під-завдання, створене для відновлення кроку parent_prefix
            goal_description = f"Recovery sub-tasks for step {parent_prefix}"
            try:
                shared_context.push_goal(goal_description, total_steps=len(steps))
                goal_pushed = True
                logger.info(
                    f"[ORCHESTRATOR] 🎯 Entering recursive level {depth}: {goal_description}"
                )

                # Оновити metadata_blob в БД для збереження рекурсивного контексту
                await self._update_task_metadata()

            except Exception as e:
                logger.warning(f"Failed to push goal: {e}")
        elif depth > 0:
            # Це вкладений рівень (не повинно відбуватися без parent_prefix, але на всяк випадок)
            goal_description = f"Sub-plan at depth {depth}"
            try:
                shared_context.push_goal(goal_description, total_steps=len(steps))
                goal_pushed = True
                logger.info(
                    f"[ORCHESTRATOR] 🎯 Entering recursive level {depth}: {goal_description}"
                )

                # Оновити metadata_blob в БД для збереження рекурсивного контексту
                await self._update_task_metadata()

            except Exception as e:
                logger.warning(f"Failed to push goal: {e}")

        for i, step in enumerate(steps):
            # Generate hierarchical ID: "1", "2" or "3.1", "3.2"
            if parent_prefix:
                step_id = f"{parent_prefix}.{i + 1}"
            else:
                step_id = str(i + 1)

            # Update step object with this dynamic ID (for logging/recovery context)
            step["id"] = step_id

            notifications.show_progress(i + 1, len(steps), f"[{step_id}] {step.get('action')}")

            # Update current step progress in shared context (не push_goal!)
            try:
                from src.brain.context import shared_context

                shared_context.current_step_id = i + 1
            except (ImportError, NameError, AttributeError):
                pass

            # --- SKIP ALREADY COMPLETED STEPS ---
            step_results = self.state.get("step_results") or []
            if any(
                isinstance(res, dict)
                and str(res.get("step_id")) == str(step_id)
                and res.get("success")
                for res in step_results
            ):
                logger.info(f"[ORCHESTRATOR] Skipping already completed step {step_id}")
                continue

            # Retry loop with Dynamic Temperature
            max_step_retries = 3
            last_error = ""

            for attempt in range(1, max_step_retries + 1):
                step_result: StepResult | None = None
                await self._log(
                    f"Step {step_id}, Attempt {attempt}: {step.get('action')}",
                    "orchestrator",
                )

                try:
                    step_result = await asyncio.wait_for(
                        self.execute_node(
                            cast("TrinityState", self.state),
                            step,
                            step_id,
                            attempt=attempt,
                            depth=depth,
                        ),
                        timeout=float(config.get("orchestrator", {}).get("task_timeout", 1200.0))
                        + 60.0,
                    )
                    if step_result and step_result.success:
                        logger.info(f"[ORCHESTRATOR] Step {step_id} completed successfully")
                        break
                    if step_result:
                        last_error = step_result.error or "Step failed without error message"
                        logger.warning(
                            f"[ORCHESTRATOR] Step {step_id} failed. Error: {last_error}. Tool: {step_result.tool_call.get('name') if step_result.tool_call else 'N/A'}"
                        )
                    else:
                        last_error = "Unknown execution error (no result returned)"
                        logger.error(f"[ORCHESTRATOR] Step {step_id} returned no result")

                    await self._log(
                        f"Step {step_id} Attempt {attempt} failed: {last_error}",
                        "warning",
                    )

                except TimeoutError:
                    last_error = f"Step execution timeout after {config.get('orchestrator', {}).get('task_timeout', 1200.0)}s"
                    logger.error(f"[ORCHESTRATOR] Step {step_id} timed out on attempt {attempt}")
                    await self._log(
                        f"Step {step_id} Attempt {attempt} timed out: {last_error}",
                        "error",
                    )
                except Exception as e:
                    last_error = f"{type(e).__name__}: {e!s}"
                    logger.error(
                        f"[ORCHESTRATOR] Step {step_id} crashed on attempt {attempt}: {last_error}",
                        exc_info=True,
                    )
                    await self._log(
                        f"Step {step_id} Attempt {attempt} crashed: {last_error}",
                        "error",
                    )

                # === SMART SELF-HEALING ROUTER ===
                strategy = error_router.decide(last_error, attempt)
                logger.info(
                    f"[ORCHESTRATOR] Recovery Strategy: {strategy.action} (Reason: {strategy.reason})"
                )

                if strategy.action == "RETRY":
                    # Simple patient retry for transient errors
                    if attempt < strategy.max_retries:
                        await self._log(
                            f"Transient error detected. {strategy.reason}. Retrying in {strategy.backoff}s...",
                            "orchestrator",
                        )
                        await asyncio.sleep(strategy.backoff)
                        continue  # Continue loop to retry
                    # If max retries exhausted, flow down to fallback (or escalation)

                elif strategy.action == "WAIT_AND_RETRY":
                    # Infrastructure errors: API rate limits, service unavailability
                    # Don't involve Vibe/Grisha - these are external issues
                    if attempt < strategy.max_retries:
                        await self._log(
                            f"Infrastructure issue detected. {strategy.reason}. Waiting {strategy.backoff}s...",
                            "orchestrator",
                        )
                        await asyncio.sleep(strategy.backoff)
                        continue  # Continue loop to retry
                    else:
                        # After all retries exhausted, notify user
                        await self._log(
                            f"Persistent infrastructure issue: {strategy.reason}. User intervention needed.",
                            "error",
                        )
                        step_result = StepResult(
                            step_id=step_id,
                            success=False,
                            error="infrastructure_failure",
                            result=f"API rate limit or service unavailability persisted after {attempt} attempts. {strategy.reason}",
                        )
                        break

                elif strategy.action == "RESTART":
                    # Critical State Error
                    await self._log(
                        f"CRITICAL: {strategy.reason}. Initiating System Restart...",
                        "system",
                        type="error",
                    )

                    # Safe Redis access
                    redis_client = getattr(state_manager, "redis", None)

                    # Save state immediately
                    if state_manager and state_manager.available:
                        await state_manager.save_session(self.current_session_id, self.state)
                        if redis_client:
                            restart_metadata = {
                                "reason": strategy.reason,
                                "timestamp": datetime.now().isoformat(),
                                "source": "orchestrator_self_healing",
                            }
                            await redis_client.set("restart_pending", json.dumps(restart_metadata))

                    # Execute Restart
                    import os
                    import sys

                    logger.info("[ORCHESTRATOR] Executing os.execv restart now...")
                    await asyncio.sleep(1.0)  # Give logs time to flush
                    os.execv(sys.executable, [sys.executable, *sys.argv])
                    return False  # Stop current execution

                elif strategy.action == "ASK_USER":
                    await self._log(f"Permission/Input required: {strategy.reason}", "orchestrator")
                    # Flow continues to user input handling logic below or breaks retry loop to ask user
                    # Integration with 'need_user_input' logic
                    # For now we break to let the loop finish and potentially ask user via result.error="need_user_input"
                    # But here we are in Exception block, so we might need to synthesize a result
                    step_result = StepResult(
                        step_id=step_id,
                        success=False,
                        error="need_user_input",
                        result=strategy.reason,
                    )
                    break

                elif strategy.action == "VIBE_HEAL":
                    # Logic/Complex Error -> Engage Vibe immediately
                    await self._log(
                        f"Logic Error: {strategy.reason}. Engaging Vibe Self-Healing...", "orchestrator"
                    )
                    heal_success, heal_result = await self._self_heal(
                        step, step_id, last_error, step_result, depth
                    )

                    if heal_result:
                        # Rejection or fatal error returned as result
                        step_result = heal_result
                        break

                    if heal_success:
                        await self._log(f"[ORCHESTRATOR] Healing applied for {step_id}. Retrying...", "orchestrator")
                        continue
                    
                    # If healing failed, fall through to fallback (Atlas Help)
                    await self._log(f"[ORCHESTRATOR] Healing failed for {step_id}. Attempting fallback...", "warning")

                elif strategy.action == "ATLAS_PLAN":
                    await self._log(
                        f"Strategic Recovery: {strategy.reason}. Escalating to Atlas for plan update...",
                        "orchestrator",
                    )
                    try:
                        # Request a strategic pivot from Atlas
                        replan_query = f"RECOVERY STRATEGY NEEDED. Goal: {self.state.get('current_goal')}. Step {step_id} failed with error: {last_error}."
                        # Create an enriched request for Atlas.create_plan
                        enriched = {
                            "enriched_request": replan_query,
                            "intent": "task",
                            "complexity": "medium",
                        }
                        new_plan = await self.atlas.create_plan(enriched)

                        if new_plan and hasattr(new_plan, "steps") and new_plan.steps:
                            await self._log(
                                f"Atlas provided a recovery sub-plan with {len(new_plan.steps)} steps. Inserting...",
                                "orchestrator",
                            )
                            # Insert these steps into the current list to be executed next
                            for offset, s in enumerate(new_plan.steps):
                                steps.insert(i + 1 + offset, s)
                            continue  # Move to the next step (which is now the first recovery step)
                    except Exception as e:
                        logger.error(f"Atlas re-planning failed: {e}")

                # ... fall through to existing Vibe/Atlas recovery logic if action is VIBE_HEAL ...

                # RECOVERY LOGIC (Legacy + Vibe Integration)
                validate_with_grisha = bool(
                    config.get("orchestrator", {}).get("validate_failed_steps_with_grisha", False),
                )
                recovery_agent = config.get("orchestrator", {}).get("recovery_voice_agent", "atlas")

                if validate_with_grisha:
                    try:
                        await self._log(
                            f"Requesting Grisha validation for failed step {step_id}...",
                            "orchestrator",
                        )
                        screenshot = None
                        expected = step.get("expected_result", "").lower()
                        if any(
                            k in expected
                            for k in ["visual", "screenshot", "ui", "interface", "window"]
                        ):
                            screenshot = await self.grisha.take_screenshot()

                        try:
                            from src.brain.context import shared_context

                            goal_ctx = str(shared_context.get_goal_context() or "")
                        except (ImportError, NameError):
                            goal_ctx = ""

                        verify_result = await self.grisha.verify_step(
                            step=step,
                            result=step_result
                            if step_result is not None
                            else StepResult(
                                step_id=step_id,
                                success=False,
                                result="",
                                error=last_error,
                            ),
                            screenshot_path=screenshot,
                            goal_context=goal_ctx,
                            task_id=str(self.state.get("db_task_id") or ""),
                        )

                        if verify_result.verified:
                            await self._log(
                                f"Grisha verified step {step_id} despite reporting failure. Marking success.",
                                "orchestrator",
                            )
                            break
                        await self._speak(
                            recovery_agent,
                            verify_result.voice_message or "Крок потребує відновлення.",
                        )
                    except Exception as e:
                        logger.warning(f"Grisha validation failed: {e}")

                notifications.send_stuck_alert(
                    int(str(step_id).split(".")[-1])
                    if "." in str(step_id)
                    else (
                        int(step_id)
                        if isinstance(step_id, int | str) and str(step_id).isdigit()
                        else 0
                    ),
                    str(last_error or "Unknown error"),
                    max_step_retries,
                )

                await self._log(
                    f"Recovery for Step {step_id} (announced by {recovery_agent})...",
                    "orchestrator",
                )
                if recovery_agent == "atlas":
                    await self._speak(
                        "atlas",
                        self.atlas.get_voice_message("recovery_started", step_id=step_id),
                    )
                else:
                    await self._speak(
                        recovery_agent,
                        "Крок зупинився — починаю процедуру відновлення.",
                    )

                # Fallback to Atlas Help if explicit strategies failed or were skipped


                # Standard Atlas help as fallback
                try:
                    recovery = await asyncio.wait_for(
                        self.atlas.help_tetyana(str(step_id), str(last_error)),
                        timeout=60.0,
                    )
                    await self._speak(
                        "atlas",
                        recovery.get("voice_message", "Альтернативний шлях."),
                    )
                    alt_steps = recovery.get("alternative_steps", [])
                    if alt_steps:
                        # --- RECURSION GUARD ---
                        # Check if this exact set of steps was already attempted at this depth
                        steps_hash = hash(str(alt_steps))
                        if not hasattr(self, "_attempted_recoveries"):
                            self._attempted_recoveries: dict[str, int] = {}
                        
                        if self._attempted_recoveries.get(step_id) == steps_hash:
                            logger.error(f"[ORCHESTRATOR] Atlas suggested a redundant recovery sub-plan for {step_id}. Breaking loop to prevent stall.")
                            raise Exception(f"Recursive recovery stall detected for step {step_id}.")
                        
                        self._attempted_recoveries[step_id] = steps_hash
                        
                        # CRITICAL: Check max depth before recursion
                        from src.brain.context import shared_context
                        if shared_context.is_at_max_depth(depth + 1):
                            logger.error(f"[ORCHESTRATOR] Max recursion depth exceeded at depth {depth+1}. Cannot subdivide {step_id}.")
                            raise Exception(f"Maximum recursion depth exceeded. Task halted at step {step_id}.")

                        # Recursive execution of sub-tasks
                        await self._execute_steps_recursive(
                            alt_steps,
                            parent_prefix=step_id,
                            depth=depth + 1,
                        )
                        # If recursion returns, we consider the step fixed
                        break
                except Exception as r_err:
                    logger.error(f"Atlas recovery failed: {r_err}")
                    raise Exception(
                        f"Task failed at step {step_id} after retries and recovery attempts.",
                    )

            # End of retry loop for THIS step
            # НЕ викликаємо pop_goal тут - він викликається тільки в кінці рекурсії

        # POP GOAL: Виходимо з під-завдання (рекурсивний рівень)
        if goal_pushed:
            try:
                completed_goal = shared_context.pop_goal()
                logger.info(
                    f"[ORCHESTRATOR] ✅ Completed recursive level {depth}: {completed_goal}"
                )

                # Оновити metadata_blob в БД після виходу з рекурсії
                await self._update_task_metadata()

            except Exception as e:
                logger.warning(f"Failed to pop goal: {e}")

        return True

    async def execute_node(
        self,
        state: TrinityState,
        step: dict[str, Any],
        step_id: str,
        attempt: int = 1,
        depth: int = 0,
    ) -> StepResult:
        """Atomic execution logic with recursion and dynamic temperature"""
        # Starting message logic
        # Simple heuristic: If it's a top level step (no dots) and first attempt
        if "." not in str(step_id) and attempt == 1:
            # Use voice_action from plan if available, else fallback to generic
            msg = step.get("voice_action")
            if not msg:
                msg = self.tetyana.get_voice_message(
                    "starting",
                    step=step_id,
                    description=step.get("action", ""),
                )
            await self._speak("tetyana", msg)
        elif "." in str(step_id):
            # It's a sub-step/recovery step
            pass

        try:
            from src.brain.state_manager import state_manager

            if state_manager and getattr(state_manager, "available", False):
                await state_manager.publish_event(
                    "steps",
                    {
                        "type": "step_started",
                        "step_id": str(step_id),
                        "action": step.get("action", "Working..."),
                        "attempt": attempt,
                    },
                )
        except (ImportError, NameError):
            pass
        # DB Step logging
        db_step_id = None
        self.state["db_step_id"] = None
        try:
            from src.brain.db.manager import db_manager

            if (
                db_manager
                and getattr(db_manager, "available", False)
                and self.state.get("db_task_id")
            ):
                async with await db_manager.get_session() as db_sess:
                    new_step = DBStep(
                        task_id=self.state["db_task_id"],
                        sequence_number=str(step_id),
                        action=f"[{step_id}] {step.get('action', '')}",
                        tool=step.get("tool", ""),
                        status="RUNNING",
                    )
                    db_sess.add(new_step)
                    await db_sess.commit()
                    db_step_id = str(new_step.id)
                    self.state["db_step_id"] = db_step_id
        except Exception as e:
            logger.error(f"DB Step creation failed: {e}")

        step_start_time = asyncio.get_event_loop().time()

        if step.get("type") == "subtask" or step.get("tool") == "subtask":
            self._in_subtask = True
            try:
                sub_result = await self.run(str(step.get("action") or ""))
            finally:
                self._in_subtask = False

            result = StepResult(
                step_id=str(step.get("id") or step_id),
                success=sub_result.get("status") == "completed",
                result="Subtask completed",
                error=str(sub_result.get("error") or ""),
            )
        else:
            try:
                # Inject context results (last 10 for better relevance)
                step_copy = step.copy()
                if self.state and "step_results" in self.state:
                    step_copy["previous_results"] = self.state["step_results"][-10:]

                # Inject critical discoveries for cross-step data access
                discoveries_summary = shared_context.get_discoveries_summary()
                if discoveries_summary:
                    step_copy["critical_discoveries"] = discoveries_summary

                # Full plan for sequence context
                plan = self.state.get("current_plan")
                if plan:
                    # Convert plan steps to a readable summary
                    step_list = []
                    plan_steps = getattr(plan, "steps", [])
                    if isinstance(plan_steps, list):
                        for s in plan_steps:
                            s_dict = s if isinstance(s, dict) else {}
                            step_results = self.state.get("step_results") or []
                            status = (
                                "DONE"
                                if any(
                                    isinstance(res, dict)
                                    and str(res.get("step_id")) == str(s_dict.get("id"))
                                    and res.get("success")
                                    for res in step_results
                                )
                                else "PENDING"
                            )
                            step_list.append(
                                f"Step {s_dict.get('id')}: {s_dict.get('action')} [{status}]",
                            )
                    step_copy["full_plan"] = "\n".join(step_list)

                # Check message bus for specific feedback from other agents
                bus_messages = await message_bus.receive("tetyana", mark_read=True)
                if bus_messages:
                    step_copy["bus_messages"] = [m.to_dict() for m in bus_messages]

                result = await self.tetyana.execute_step(step_copy, attempt=attempt)

                # --- RESTART DETECTION ---
                try:
                    from src.brain.state_manager import state_manager

                    if state_manager and getattr(state_manager, "available", False):
                        restart_key = state_manager._key("restart_pending")
                        try:
                            if state_manager.redis_client and await state_manager.redis_client.exists(
                                restart_key,
                            ):
                                logger.warning(
                                    "[ORCHESTRATOR] Imminent application restart detected. Saving session state immediately.",
                                )
                                await state_manager.save_session(
                                    self.current_session_id,
                                    self.state,
                                )
                                # We stop here. The process replacement (execv) will happen in ToolDispatcher task
                                # and this orchestrator task will either be killed or return soon.
                        except Exception:
                            pass
                except (ImportError, NameError):
                    pass

                # --- DYNAMIC AGENCY: Check for Strategy Deviation ---
                # --- DYNAMIC AGENCY: Check for Strategy Deviation ---
                if getattr(result, "is_deviation", False) or result.error == "strategy_deviation":
                    try:
                        proposal_text = (
                            result.deviation_info.get("analysis")
                            if getattr(result, "deviation_info", None)
                            else result.result
                        )
                        p_text = str(proposal_text)
                        logger.warning(
                            f"[ORCHESTRATOR] Tetyana proposed a deviation: {p_text[:200]}...",
                        )

                        # Consult Atlas
                        evaluation = await self.atlas.evaluate_deviation(
                            step,
                            str(proposal_text),
                            getattr(self.state.get("current_plan"), "steps", []),
                        )

                        voice_msg = evaluation.get("voice_message", "")
                        if voice_msg:
                            await self._speak("atlas", voice_msg)

                        if evaluation.get("approved"):
                            logger.info("[ORCHESTRATOR] Deviation APPROVED. Adjusting plan...")
                            result.success = True
                            result.result = f"Strategy Deviated: {evaluation.get('reason')}"
                            result.error = None

                            # Mark for behavioral learning after successful verification
                            result.is_deviation = True
                            result.deviation_info = evaluation

                            # PERSISTENCE: Remember this approved deviation immediately
                            try:
                                from src.brain.memory import long_term_memory

                                if long_term_memory and getattr(
                                    long_term_memory,
                                    "available",
                                    False,
                                ):
                                    reason_text = str(evaluation.get("reason", "Unknown"))
                                    long_term_memory.remember_behavioral_change(
                                        original_intent=step.get("action", ""),
                                        deviation=p_text[:300],
                                        reason=reason_text,
                                        result="Deviated plan approved",
                                        context={
                                            "step_id": str(self.state.get("db_step_id") or ""),
                                            "sequence_id": str(step_id),
                                            "session_id": self.state.get("session_id"),
                                            "db_session_id": self.state.get("db_session_id"),
                                        },
                                        decision_factors={
                                            "original_step": step,
                                            "analysis": proposal_text,
                                        },
                                    )
                                    logger.info(
                                        "[ORCHESTRATOR] Learned and memorized new behavioral deviation strategy.",
                                    )
                            except (ImportError, NameError) as mem_err:
                                logger.warning(f"Failed to memorize deviation: {mem_err}")

                        else:
                            logger.info("[ORCHESTRATOR] Deviation REJECTED. Forcing original plan.")
                            step["grisha_feedback"] = (
                                f"Strategy Deviation Rejected: {evaluation.get('reason')}. Stick to the plan."
                            )
                            result.success = False
                    except Exception as eval_err:
                        logger.error(f"[ORCHESTRATOR] Deviation evaluation failed: {eval_err}")
                        result.success = False
                        result.error = "evaluation_error"
                        return cast(StepResult, result)

                # Handle need_user_input signal (New Autonomous Timeout Logic)
                if result.error == "need_user_input":
                    # Speak Tetyana's request BEFORE waiting to inform the user immediately
                    if result.voice_message:
                        await self._speak("tetyana", result.voice_message)
                        result.voice_message = (
                            None  # Clear it so it won't be spoken again at the end of node
                        )

                    timeout_val = float(config.get("orchestrator.user_input_timeout", 12.0))
                    await self._log(
                        f"User input needed for step {step_id}. Waiting {timeout_val} seconds...",
                        "orchestrator",
                    )

                    # Display the question to the user in the logs/UI
                    await self._log(f"[REQUEST] {result.result}", "system", type="warning")

                    # Wait for user message on the bus or timeout
                    user_response = None
                    try:
                        # Wait for a 'user_response' message type specifically for this step
                        start_wait = asyncio.get_event_loop().time()
                        while asyncio.get_event_loop().time() - start_wait < timeout_val:
                            bus_msgs = await message_bus.receive("orchestrator", mark_read=True)
                            for m in bus_msgs:
                                if m.message_type == MessageType.CHAT and m.from_agent == "USER":
                                    user_response = m.payload.get("text")
                                    break
                            if user_response:
                                break
                            await asyncio.sleep(0.5)

                    except Exception as wait_err:
                        logger.warning(f"Error during user wait: {wait_err}")

                    if user_response:
                        await self._log(f"User responded: {user_response}", "system")
                        messages = self.state.get("messages")
                        if messages is not None and isinstance(messages, list):
                            messages.append(HumanMessage(content=user_response))
                            self.state["messages"] = messages
                        try:
                            from src.brain.state_manager import state_manager

                            if state_manager and getattr(state_manager, "available", False):
                                await state_manager.save_session("current_session", self.state)
                        except (ImportError, NameError):
                            pass

                        # Direct feedback for the next retry
                        await message_bus.send(
                            AgentMsg(
                                from_agent="USER",
                                to_agent="tetyana",
                                message_type=MessageType.FEEDBACK,
                                payload={"user_response": user_response},
                                step_id=step.get("id"),
                            ),
                        )
                        result.success = False
                        result.error = "user_input_received"
                    else:
                        # TIMEOUT: Atlas ONLY speaks if user was truly silent
                        await self._log(
                            "User silent for timeout. Atlas deciding...",
                            "orchestrator",
                            type="warning",
                        )

                        def _get_msg_content(m):
                            if hasattr(m, "content"):
                                return m.content
                            if isinstance(m, dict):
                                return m.get("content", str(m))
                            return str(m)

                        messages = self.state.get("messages", [])
                        goal_msg = messages[0] if messages else HumanMessage(content="Unknown")

                        autonomous_decision = await self.atlas.decide_for_user(
                            str(result.result or ""),
                            {
                                "goal": _get_msg_content(goal_msg),
                                "current_step": str(step.get("action") or ""),
                                "history": [
                                    _get_msg_content(m) for m in (messages[-5:] if messages else [])
                                ],
                            },
                        )

                        await self._log(
                            f"Atlas Autonomous Decision (Timeout): {autonomous_decision}",
                            "atlas",
                        )
                        await self._speak(
                            "atlas",
                            f"Оскільки ви не відповіли, я вирішив: {autonomous_decision}",
                        )

                        # Inject decision as feedback
                        await message_bus.send(
                            AgentMsg(
                                from_agent="atlas",
                                to_agent="tetyana",
                                message_type=MessageType.FEEDBACK,
                                payload={
                                    "user_response": f"(Autonomous Decision): {autonomous_decision}",
                                },
                                step_id=step.get("id"),
                            ),
                        )
                        result.success = False
                        result.error = "autonomous_decision_made"

                # Log tool execution to DB for Grisha's audit
                try:
                    from src.brain.db.manager import db_manager

                    if db_manager and getattr(db_manager, "available", False) and db_step_id:
                        async with await db_manager.get_session() as db_sess:
                            tool_call_data = result.tool_call or {}
                            tool_exec = DBToolExecution(
                                step_id=db_step_id,
                                task_id=self.state.get("db_task_id"),  # Direct link for analytics
                                server_name=tool_call_data.get("server")
                                or tool_call_data.get("realm")
                                or "unknown",
                                tool_name=tool_call_data.get("name") or "unknown",
                                arguments=tool_call_data.get("args") or {},
                                result=str(result.result)[:10000],  # Cap size
                            )

                            db_sess.add(tool_exec)
                            await db_sess.commit()
                            logger.info(
                                f"[ORCHESTRATOR] Logged tool execution: {tool_exec.tool_name}",
                            )
                except Exception as e:
                    logger.error(f"Failed to log tool execution to DB: {e}")

                # Handle proactive help requested by Tetyana
                if result.error == "proactive_help_requested":
                    await self._log(
                        f"Tetyana requested proactive help: {result.result}",
                        "orchestrator",
                    )
                    # Atlas help logic
                    history_results = self.state.get("step_results")
                    if not isinstance(history_results, list):
                        history_results = []

                    help_resp = await self.atlas.help_tetyana(
                        str(step.get("id") or step_id),
                        str(result.result or ""),
                        history=history_results,
                    )

                    # Extract voice message or reason from Atlas response
                    voice_msg = ""
                    if isinstance(help_resp, dict):
                        voice_msg = (
                            help_resp.get("voice_message")
                            or help_resp.get("reason")
                            or str(help_resp)
                        )
                    else:
                        voice_msg = str(help_resp)

                    await self._speak("atlas", voice_msg)

                    # NEW: Support hierarchical recovery via alternative_steps
                    alt_steps = None
                    if isinstance(help_resp, dict):
                        alt_steps = help_resp.get("alternative_steps")

                    if alt_steps and isinstance(alt_steps, list):
                        await self._log(
                            f"Atlas provided {len(alt_steps)} alternative steps. Executing recovery sub-plan...",
                            "orchestrator",
                        )
                        # Execute the sub-steps recursively
                        success = await self._execute_steps_recursive(
                            alt_steps, parent_prefix=str(step.get("id") or step_id), depth=depth + 1
                        )
                        if success:
                            await self._log(
                                f"Recovery sub-plan for {step_id} completed successfully. Retrying original step with new context.",
                                "orchestrator",
                            )
                            # We don't return success yet, we want to retry the original step
                            # now that we (hopefully) have the missing info in context.
                        else:
                            await self._log(f"Recovery sub-plan for {step_id} failed.", "error")

                    # Re-run the step with Atlas's guidance as bus feedback
                    await message_bus.send(
                        AgentMsg(
                            from_agent="atlas",
                            to_agent="tetyana",
                            message_type=MessageType.FEEDBACK,
                            payload={"guidance": help_resp},
                            step_id=step.get("id"),
                        ),
                    )
                    # Mark result as "Help pending" so retry loop can pick it up
                    result.success = False
                    result.error = "help_pending"

                # Log interaction to Knowledge Graph if successful
                if result.success and result.tool_call:
                    await knowledge_graph.add_node(
                        node_type="TOOL",
                        node_id=f"tool:{result.tool_call.get('name')}",
                        attributes={"last_used_step": str(step_id), "success": True},
                    )
                    await knowledge_graph.add_edge(
                        source_id=f"task:{self.state.get('db_task_id', 'unknown')}",
                        target_id=f"tool:{result.tool_call.get('name')}",
                        relation="USED",
                    )
                if result.voice_message:
                    await self._speak("tetyana", result.voice_message)
            except Exception as e:
                logger.exception("Tetyana execution crashed")
                result = StepResult(
                    step_id=str(step.get("id") or step_id),
                    success=False,
                    result="Crashed",
                    error=str(e),
                )

        # Update DB Step
        try:
            from src.brain.db.manager import db_manager

            if db_manager and getattr(db_manager, "available", False) and db_step_id:
                try:
                    duration_ms = int((asyncio.get_event_loop().time() - step_start_time) * 1000)
                    async with await db_manager.get_session() as db_sess:
                        from sqlalchemy import update

                        await db_sess.execute(
                            update(DBStep)
                            .where(DBStep.id == db_step_id)
                            .values(
                                status="SUCCESS" if result.success else "FAILED",
                                error_message=result.error,
                                duration_ms=duration_ms,
                            ),
                        )
                        await db_sess.commit()
                except Exception as e:
                    logger.error(f"DB Step update failed: {e}")
        except (ImportError, NameError):
            pass

        # Check verification
        if step.get("requires_verification"):
            self.state["system_state"] = SystemState.VERIFYING.value
            # Removed redundant speak call here.
            # Tetyana's execute_step already provides result.voice_message if successful.

            try:
                # OPTIMIZATION: Reduced delay from 2.5s to 0.5s
                await self._log("Preparing verification...", "system")
                await asyncio.sleep(0.5)

                # Only take screenshot if visual verification is needed
                expected = step.get("expected_result", "").lower()
                visual_verification_needed = (
                    "visual" in expected
                    or "screenshot" in expected
                    or "ui" in expected
                    or "interface" in expected
                    or "window" in expected
                )

                screenshot = None
                if visual_verification_needed:
                    screenshot = await self.grisha.take_screenshot()

                # GRISHA'S AWARENESS: Pass the full result (including thoughts) and the goal
                verify_result = await self.grisha.verify_step(
                    step=step,
                    result=result,
                    screenshot_path=screenshot,
                    goal_context=shared_context.get_goal_context(),
                    task_id=str(self.state.get("db_task_id") or ""),
                )
                if not verify_result.verified:
                    result.success = False
                    result.error = f"Grisha rejected: {verify_result.description}"
                    if verify_result.issues:
                        result.error += f" Issues: {', '.join(verify_result.issues)}"

                    await self._speak(
                        "grisha",
                        verify_result.voice_message or "Результат не прийнято.",
                    )
                else:
                    await self._speak(
                        "grisha",
                        verify_result.voice_message or "Підтверджую виконання.",
                    )

                    # --- BEHAVIORAL LEARNING: Commit successful deviations ---
                    if result.is_deviation and result.success and result.deviation_info:
                        evaluation = result.deviation_info
                        factors = evaluation.get("decision_factors", {})

                        # 1. Vector Memory
                        try:
                            from src.brain.memory import long_term_memory

                            if long_term_memory and getattr(long_term_memory, "available", False):
                                long_term_memory.remember_behavioral_change(
                                    original_intent=str(step.get("action") or "Unknown"),
                                    deviation=str(result.result),
                                    reason=str(evaluation.get("reason") or "Unknown"),
                                    result="Verified Success",
                                    context={
                                        "step_id": str(step.get("id") or step_id),
                                        "session_id": self.state.get("session_id"),
                                        "db_session_id": self.state.get("db_session_id"),
                                    },
                                    decision_factors=factors,
                                )
                        except (ImportError, NameError):
                            pass

                        # 2. Knowledge Graph (Structured Factors)
                        if knowledge_graph:
                            try:
                                lesson_id = f"lesson:{int(datetime.now().timestamp())}"
                                await knowledge_graph.add_node(
                                    node_type="LESSON",
                                    node_id=lesson_id,
                                    attributes={
                                        "name": f"Successful Deviation: {str(evaluation.get('reason') or '')[:50]}",
                                        "intent": str(step.get("action") or ""),
                                        "outcome": "Verified Success",
                                        "reason": str(evaluation.get("reason") or ""),
                                    },
                                )
                                # Link to task
                                if self.state.get("db_task_id"):
                                    await knowledge_graph.add_edge(
                                        f"task:{self.state.get('db_task_id')}",
                                        lesson_id,
                                        "learned_lesson",
                                    )

                                # Structured Factor Nodes
                                for f_name, f_val in factors.items():
                                    factor_node_id = (
                                        f"factor:{f_name}:{str(f_val).lower().replace(' ', '_')}"
                                    )
                                    await knowledge_graph.add_node(
                                        "FACTOR",
                                        factor_node_id,
                                        {
                                            "name": f_name,
                                            "value": f_val,
                                            "type": "environmental_factor",
                                        },
                                    )
                                    await knowledge_graph.add_edge(
                                        lesson_id,
                                        factor_node_id,
                                        "CONTINGENT_ON",
                                    )

                            except Exception as g_err:
                                logger.error(
                                    f"[ORCHESTRATOR] Error linking factors in graph: {g_err}",
                                )
            except Exception as e:
                print(f"[ERROR] Verification failed: {e}")
                await self._log(f"Verification crashed: {e}", "error")
                result.success = False
                result.error = f"Verification system error: {e!s}"

            self.state["system_state"] = SystemState.EXECUTING.value

        # Store final result
        self.state["step_results"].append(
            {
                "step_id": str(result.step_id),  # Ensure string
                "action": f"[{step_id}] {step.get('action')}",  # Adding ID context
                "success": result.success,
                "result": result.result,
                "error": result.error,
            },
        )

        # Extract and store critical discoveries from successful steps
        if result.success and result.result:
            self._extract_and_store_discoveries(result.result, step)

        try:
            from src.brain.state_manager import state_manager

            if state_manager and getattr(state_manager, "available", False):
                await state_manager.publish_event(
                    "steps",
                    {
                        "type": "step_finished",
                        "step_id": str(step_id),
                        "success": result.success,
                        "error": result.error,
                        "result": result.result,
                    },
                )
        except (ImportError, NameError):
            pass

        # Knowledge Graph Sync
        kg_task = asyncio.create_task(self._update_knowledge_graph(step_id, result))
        self._background_tasks.add(kg_task)
        kg_task.add_done_callback(self._background_tasks.discard)

        return result

    async def planner_node(self, state: TrinityState) -> dict[str, Any]:
        return {"system_state": SystemState.PLANNING.value}

    async def executor_node(self, state: TrinityState) -> dict[str, Any]:
        return {"system_state": SystemState.EXECUTING.value}

    async def verifier_node(self, state: TrinityState) -> dict[str, Any]:
        return {"system_state": SystemState.VERIFYING.value}

    def should_verify(self, state: TrinityState) -> str:
        """Determines the next state based on config-driven rules."""
        from src.brain.behavior_engine import behavior_engine

        # Build context for rule evaluation
        context = {
            "has_error": bool(state.get("error")),
            "task_completed": state.get("system_state") == SystemState.COMPLETED.value,
            "needs_verification": False,  # Dynamic check based on plan or state
        }

        # Check if current plan indicates completion
        if state.get("current_plan") and not state.get("error"):
            # Simple check: if all steps have results, it might be completed
            plan = state["current_plan"]
            if isinstance(plan, list) and len(plan) == len(state.get("step_results", [])):
                context["task_completed"] = True
                context["needs_verification"] = True  # Default to verify before ending

        result = behavior_engine.evaluate_rule("should_verify", context)
        return str(result or "continue")

    async def shutdown(self):
        """Clean shutdown of system components"""
        logger.info("[ORCHESTRATOR] Shutting down...")
        try:
            from src.brain.mcp_manager import mcp_manager

            await mcp_manager.shutdown()
        except Exception:
            pass
        try:
            from src.brain.db.manager import db_manager

            await db_manager.close()
        except Exception:
            pass
        import contextlib

        with contextlib.suppress(Exception):
            await self.voice.close()
        logger.info("[ORCHESTRATOR] Shutdown complete.")

    async def _update_knowledge_graph(self, step_id: str, result: StepResult):
        """Background task to sync execution results to Knowledge Graph"""
        try:
            from src.brain.knowledge_graph import knowledge_graph

            if knowledge_graph:
                await knowledge_graph.add_node(
                    node_type="STEP_EXECUTION",
                    node_id=f"exec:{self.state.get('db_task_id')}:{step_id}",
                    attributes={
                        "success": result.success,
                        "error": result.error,
                        "timestamp": datetime.now(UTC).isoformat(),
                    },
                )
        except Exception as e:
            logger.error(f"Failed to update knowledge graph: {e}")

    def _extract_and_store_discoveries(self, output: str, step: dict) -> None:
        """Extract and store critical values from tool output using LLM analysis.
        
        Uses lightweight LLM call to dynamically identify important values
        instead of hardcoded patterns. Stores in both SharedContext (fast access)
        and ChromaDB (persistent semantic search).
        """
        # Skip if output is too short or empty
        if not output or len(output.strip()) < 10:
            return
        
        # Skip common non-informative outputs
        skip_patterns = ["success", "done", "completed", "ok", "true", "false"]
        if output.strip().lower() in skip_patterns:
            return
        
        step_id = str(step.get("id", "unknown"))
        step_action = step.get("action", "")[:100]
        task_id = str(self.state.get("db_task_id") or self.state.get("session_id") or "unknown")
        
        # Schedule async LLM extraction in background
        asyncio.create_task(
            self._llm_extract_discoveries(output, step_id, step_action, task_id)
        )

    async def _llm_extract_discoveries(
        self, output: str, step_id: str, step_action: str, task_id: str
    ) -> None:
        """Background LLM-based discovery extraction."""
        from langchain_core.messages import HumanMessage, SystemMessage

        from providers.copilot import CopilotLLM
        from src.brain.memory import long_term_memory
        
        try:
            # Use fast model for extraction
            extraction_model = config.get("models.chat") or config.get("models.default")
            llm = CopilotLLM(model_name=extraction_model)
            
            prompt = f"""Analyze this tool output and extract CRITICAL VALUES that should be remembered for later steps.

OUTPUT:
{output[:2000]}

STEP CONTEXT: {step_action}

Extract values that are:
- IP addresses, hostnames, or URLs
- File paths (especially keys, configs, credentials)
- MAC addresses or device identifiers
- Usernames, ports, service names
- Any specific values that would be needed in subsequent steps

Respond ONLY with valid JSON array (or empty [] if nothing important):
[
  {{"key": "descriptive_name", "value": "actual_value", "category": "ip_address|path|credential|identifier|other"}}
]

IMPORTANT: Extract ONLY concrete values, not descriptions. If nothing critical, return []"""

            messages = [
                SystemMessage(content="You are a precise data extractor. Return only valid JSON."),
                HumanMessage(content=prompt),
            ]
            
            response = await llm.ainvoke(messages)
            response_text = str(response.content).strip()
            
            # Parse JSON response
            # Handle markdown code blocks
            if "```" in response_text:
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                if json_match:
                    response_text = json_match.group(1)
            
            discoveries = json.loads(response_text)
            
            if not discoveries or not isinstance(discoveries, list):
                return
            
            for item in discoveries:
                if not isinstance(item, dict):
                    continue
                    
                key = item.get("key", "unknown")
                value = item.get("value", "")
                category = item.get("category", "other")
                
                if not value:
                    continue
                
                # Store in SharedContext for immediate access
                shared_context.store_discovery(key=key, value=value, category=category)
                
                # Store in ChromaDB for persistent semantic search
                long_term_memory.remember_discovery(
                    key=key,
                    value=value,
                    category=category,
                    task_id=task_id,
                    step_id=step_id,
                    step_action=step_action,
                )
                
                logger.info(f"[ORCHESTRATOR] LLM extracted {category}:{key}={value[:50]}...")
                
        except json.JSONDecodeError as e:
            logger.debug(f"[ORCHESTRATOR] Discovery extraction returned no valid JSON: {e}")
        except Exception as e:
            logger.warning(f"[ORCHESTRATOR] Discovery extraction failed: {e}")

