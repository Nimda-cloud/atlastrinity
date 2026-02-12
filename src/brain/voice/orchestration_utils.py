import asyncio
import hashlib
import re
import sys
import time
from datetime import datetime

from langchain_core.messages import AIMessage

from src.brain.behavior.behavior_engine import behavior_engine
from src.brain.monitoring.logger import logger


class VoiceOrchestrationMixin:
    """Mixin to handle voice feedback and log callbacks for the Trinity orchestrator."""

    async def _speak(self, agent_id: str, text: str) -> None:
        """Voice wrapper with config-driven sanitization."""
        voice_config = behavior_engine.get_output_processing("voice")

        # Deduplication Logic
        msg_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        now = time.time()
        last_time = getattr(self, "_spoken_history", {}).get(msg_hash, 0)

        if now - last_time < 60:
            logger.info(f"[VOICE] Skipping duplicate message (Cooldown active): '{text[:50]}...'")
            return

        if not hasattr(self, "_spoken_history"):
            self._spoken_history = {}
        self._spoken_history[msg_hash] = now

        # Cleanup old history
        if len(self._spoken_history) > 100:
            current_time = now
            self._spoken_history = {
                k: v for k, v in self._spoken_history.items() if current_time - v < 120
            }

        # UI Chat Log
        if hasattr(self, "state") and self.state is not None:
            if "messages" not in self.state:
                self.state["messages"] = []

            msg = AIMessage(content=text, name=agent_id.upper())
            msg.additional_kwargs["timestamp"] = datetime.now().timestamp()
            self.state["messages"].append(msg)
            # This relies on _save_chat_message being available on self (Trinity)
            asyncio.create_task(self._save_chat_message("ai", text, agent_id))

        # This relies on _log being available on self (Trinity)
        await self._log(text, source=agent_id, type="voice")

        # TTS processing
        processed_text = text
        for rule in voice_config.get("sanitization_rules", []):
            pattern = rule.get("pattern")
            replacement = rule.get("replacement", "")
            if pattern:
                processed_text = re.sub(pattern, replacement, processed_text)

        processed_text = processed_text.strip()

        min_len = voice_config.get("min_length", 2)
        max_len = voice_config.get("max_length", 5000)
        if not processed_text or len(processed_text) < min_len:
            logger.info(f"[VOICE] Text too short for TTS ({len(processed_text)} chars), skipping voice")
            return
        if len(processed_text) > max_len:
            logger.info(f"[VOICE] Text too long for TTS ({len(processed_text)} chars), truncating for voice")
            processed_text = processed_text[:max_len]

        # This relies on self.voice (VoiceManager) being available on Trinity
        final_text = await self.voice.prepare_speech_text(processed_text)
        if not final_text:
            return

        print(f"[{agent_id.upper()}] Speaking: {final_text[:100]}", file=sys.stderr)

        try:
            await self.voice.speak(agent_id, final_text)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"TTS Error: {e}", file=sys.stderr)

    async def _mcp_log_voice_callback(self, msg: str, server_name: str, level: str):
        """Callback to handle live log notifications from MCP servers."""
        now = time.time()
        last_speech = getattr(self, "_last_live_speech_time", 0)

        if now - last_speech < 10:
            return

        significant_markers = ["[VIBE-THOUGHT]", "[VIBE-ACTION]", "[VIBE-LIVE]"]
        if server_name == "vibe" and any(marker in msg for marker in significant_markers):
            speech_text = msg
            for marker in significant_markers:
                speech_text = speech_text.replace(marker, "")
            speech_text = re.sub(r"[^\w\s\.,!\?]", "", speech_text).strip()

            if len(speech_text) > 5:
                # Use 'atlas' for status updates
                self._last_live_speech_time = int(now)
                asyncio.create_task(self._speak("atlas", speech_text))

    async def stop_speaking(self):
        """Immediately stop all speech."""
        # This relies on self.stop() being available on Trinity
        self.stop()
        logger.info("[VoiceManager] Stopped speaking.")
