"""AtlasTrinity Brain Server
Exposes the orchestrator via FastAPI for Electron IPC with monitoring integration
"""

import os
import time

# Suppress espnet2 UserWarning about non-writable tensors
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="espnet2.torch_utils.device_funcs")

# Import CONFIG_ROOT before using it
from .config_loader import config
from .services_manager import ServiceStatus, ensure_all_services

# Step 1: Ensure core system services (Redis, Docker) are running
# We'll run this in the background to avoid blocking server binding

# Set API keys as environment variables for internal libraries
copilot_key = config.get_api_key("copilot_api_key")
github_token = config.get_api_key("github_token")

if copilot_key:
    os.environ["COPILOT_API_KEY"] = copilot_key
    print("[Server] ✓ COPILOT_API_KEY loaded from global context")
if github_token:
    os.environ["GITHUB_TOKEN"] = github_token
    print("[Server] ✓ GITHUB_TOKEN loaded from global context")

import asyncio

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .logger import logger
from .orchestrator import Trinity
from .production_setup import run_production_setup
from .voice.stt import SpeechType, WhisperSTT

# Global instances (Trinity will now find Redis running)
trinity = Trinity()
# stt is now part of trinity orchestrator


class TaskRequest(BaseModel):
    request: str


class AudioRequest(BaseModel):
    action: str  # 'start_recording', 'stop_recording'


class SmartSTTRequest(BaseModel):
    previous_text: str = ""  # Accumulated transcript from previous chunks


# State
current_task = None
is_recording = False

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("AtlasTrinity Brain is waking up...")

    # Initialize monitoring system
    try:
        from .monitoring import monitoring_system

        monitoring_system.log_for_grafana("Server startup initiated", level="info")
    except ImportError:
        logger.warning("Monitoring system not available")

    # Initialize services in background
    asyncio.create_task(ensure_all_services())

    # Initialize components
    await trinity.initialize()

    # Production: copy configs from Resources/ to ~/.config/ if needed
    run_production_setup()

    # Production: copy configs from Resources/ to ~/.config/ if needed
    run_production_setup()

    yield
    # Shutdown
    logger.info("AtlasTrinity Brain is going to sleep...")

    # Shutdown monitoring
    try:
        from .monitoring import monitoring_system

        monitoring_system.log_for_grafana("Server shutdown initiated", level="info")
    except ImportError:
        pass

    await trinity.shutdown()


app = FastAPI(title="AtlasTrinity Brain", lifespan=lifespan)

# CORS setup for Electron
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
async def chat(task: TaskRequest, background_tasks: BackgroundTasks):
    """Send a user request to the system with monitoring"""
    if current_task and not current_task.done():
        raise HTTPException(status_code=409, detail="System is busy")

    print(f"[SERVER] Received request: {task.request}")
    logger.info(f"Received request: {task.request}")

    # Start monitoring for this request
    start_time = time.time()
    try:
        from .monitoring import monitoring_system

        monitoring_system.start_request()
        monitoring_system.log_for_grafana(
            f"Chat request started: {task.request}", level="info", request_type="chat"
        )
    except ImportError:
        pass

    # Run orchestration in background/loop
    try:
        result = await trinity.run(task.request)

        # Record successful request
        request_duration = time.time() - start_time
        try:
            from .monitoring import monitoring_system

            monitoring_system.record_request("chat", "success", request_duration)
            monitoring_system.log_for_grafana(
                f"Chat request completed: {task.request}",
                level="info",
                request_type="chat",
                duration=request_duration,
                status="success",
            )
        except ImportError:
            pass

        return {"status": "completed", "result": result}
    except asyncio.CancelledError:
        logger.info(f"Request interrupted/cancelled: {task.request}")

        # Record cancelled request
        request_duration = time.time() - start_time
        try:
            from .monitoring import monitoring_system

            monitoring_system.record_request("chat", "cancelled", request_duration)
            monitoring_system.log_for_grafana(
                f"Chat request cancelled: {task.request}",
                level="warning",
                request_type="chat",
                duration=request_duration,
                status="cancelled",
            )
        except ImportError:
            pass

        return {"status": "interrupted", "detail": "Task was cancelled by a new request"}
    except Exception as e:
        logger.exception(f"Error processing request: {task.request}")

        # Record failed request
        request_duration = time.time() - start_time
        try:
            from .monitoring import monitoring_system

            monitoring_system.record_request("chat", "error", request_duration)
            monitoring_system.log_for_grafana(
                f"Chat request failed: {task.request}",
                level="error",
                request_type="chat",
                duration=request_duration,
                status="error",
                error=str(e),
            )
        except ImportError:
            pass

        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            from .monitoring import monitoring_system

            monitoring_system.end_request()
        except ImportError:
            pass


@app.get("/api/health")
async def health():
    """Health check for UI"""
    return {"status": "ok", "version": "1.0.1"}


@app.get("/api/monitoring/metrics")
async def get_metrics():
    """Get current monitoring metrics"""
    try:
        from .monitoring import monitoring_system

        metrics = monitoring_system.get_metrics_snapshot()

        # Add system health status
        metrics["monitoring_health"] = monitoring_system.is_healthy()

        return {"status": "success", "data": metrics}
    except ImportError:
        return {"status": "error", "message": "Monitoring system not available"}
    except Exception as e:
        logger.error(f"Error getting monitoring metrics: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/monitoring/health")
async def monitoring_health():
    """Check monitoring system health"""
    try:
        from .monitoring import monitoring_system

        return {
            "status": "healthy" if monitoring_system.is_healthy() else "unhealthy",
            "prometheus_port": monitoring_system.prometheus_port,
            "opensearch_enabled": monitoring_system.opensearch_enabled,
            "grafana_enabled": monitoring_system.grafana_enabled,
        }
    except ImportError:
        return {"status": "disabled", "message": "Monitoring system not available"}


@app.post("/api/session/reset")
async def reset_session():
    """Reset current session"""
    return await trinity.reset_session()


@app.get("/api/sessions")
async def get_sessions():
    """List all available sessions"""
    from .state_manager import state_manager

    return await state_manager.list_sessions()


@app.post("/api/sessions/restore")
async def restore_session(payload: dict[str, str]):
    """Restore a specific session"""
    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    return await trinity.load_session(session_id)


@app.get("/api/state")
async def get_state():
    """Get current system state for UI polling"""
    state = trinity.get_state()

    # Enrich with service status if not all-ready
    if not ServiceStatus.is_ready:
        state["service_status"] = {
            "status": ServiceStatus.status_message,
            "details": ServiceStatus.details,
        }

    return state


@app.post("/api/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech to text using Whisper"""
    try:
        # Save uploaded audio temporarily
        import subprocess
        import tempfile

        # Determine extension based on content_type
        content_type = audio.content_type or "audio/wav"
        if "webm" in content_type:
            suffix = ".webm"
        elif "ogg" in content_type:
            suffix = ".ogg"
        elif "mp3" in content_type:
            suffix = ".mp3"
        else:
            suffix = ".wav"

        # CHECK: Is the agent currently speaking?
        if trinity.voice.is_speaking:
            logger.info("[STT] Agent is speaking, ignoring audio to avoid feedback loop.")
            return {"text": "", "confidence": 0, "ignored": True}

        logger.info(f"[STT] Received audio: content_type={content_type}, using suffix={suffix}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
            logger.info(f"[STT] Saved to: {temp_file_path}, size: {len(content)} bytes")

        # Конвертуємо webm/ogg/mp3 → wav для кращої роботи Whisper
        wav_path = temp_file_path
        if suffix != ".wav":
            wav_path = temp_file_path.replace(suffix, ".wav")
            try:
                # Optimized for Whisper large-v3: High clarity, no aggressive cutoff
                result = subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        temp_file_path,
                        "-af",
                        (
                            "highpass=f=80, "  # Remove sub-bass rumble
                            "loudnorm"  # Standardize loudness
                        ),
                        "-ar",
                        "16000",
                        "-ac",
                        "1",
                        "-f",
                        "wav",
                        wav_path,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    logger.info(f"[STT] Converted to WAV: {wav_path}")
                    os.unlink(temp_file_path)
                else:
                    logger.warning(f"[STT] FFmpeg failed: {result.stderr}, using original file")
                    wav_path = temp_file_path
            except FileNotFoundError:
                logger.warning("[STT] FFmpeg not found, using original file")
                wav_path = temp_file_path
            except subprocess.TimeoutExpired:
                logger.warning("[STT] FFmpeg timeout, using original file")
                wav_path = temp_file_path

        # Transcribe using Whisper
        result = await trinity.stt.transcribe_file(wav_path)

        # Echo cancellation: Ignore if Whisper heard the agent's own voice
        clean_text = result.text.strip().lower().replace(".", "").replace(",", "")
        last_spoken = trinity.voice.last_text.replace(".", "").replace(",", "")

        # Check for exact match OR if result is part of what agent said
        # (common issue: Whisper catching the end of agent's sentence)
        if clean_text and (
            clean_text == last_spoken
            or clean_text in last_spoken
            or (len(clean_text) > 4 and last_spoken in clean_text)
        ):
            logger.info(f"[STT] Echo detected: '{result.text}', ignoring.")
            return {"text": "", "confidence": 0, "ignored": True}

        logger.info(f"[STT] Result: text='{result.text}', confidence={result.confidence}")

        # Clean up temp file(s)
        if os.path.exists(wav_path):
            os.unlink(wav_path)
        if wav_path != temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

        return {"text": result.text, "confidence": result.confidence}

    except Exception as e:
        logger.exception(f"STT error: {e!s}")
        raise HTTPException(status_code=500, detail=str(e))


async def _prepare_audio_file(audio: UploadFile) -> tuple[str, str]:
    """Determine extension and save audio temporarily."""
    content_type = audio.content_type or "audio/wav"
    suffix = ".wav"
    if "webm" in content_type:
        suffix = ".webm"
    elif "ogg" in content_type:
        suffix = ".ogg"
    elif "mp3" in content_type:
        suffix = ".mp3"

    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        content = await audio.read()
        temp_file.write(content)
        return temp_file.name, suffix


async def _convert_to_wav(temp_file_path: str, suffix: str) -> str:
    """Convert non-WAV audio to WAV using FFmpeg."""
    if suffix == ".wav":
        return temp_file_path

    wav_path = temp_file_path.replace(suffix, ".wav")
    try:
        process = await asyncio.create_subprocess_exec(
            "ffmpeg",
            "-y",
            "-i",
            temp_file_path,
            "-af",
            "highpass=f=80, loudnorm",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-f",
            "wav",
            "-loglevel",
            "error",
            wav_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        if process.returncode == 0:
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
            return wav_path
    except Exception as e:
        logger.error(f"[STT] FFmpeg error: {e}")

    return temp_file_path


def _check_echo_and_noise(text: str, confidence: float, previous_text: str) -> bool:
    """Detect if the text is an echo of agent's speech or noise."""
    from difflib import SequenceMatcher

    now = time.time()
    trinity_voice = getattr(trinity, "voice", None)
    agent_was_speaking = trinity_voice.is_speaking if trinity_voice else False

    clean_text = (
        text.strip().lower().replace(".", "").replace(",", "").replace("!", "").replace("?", "")
    )
    if not clean_text:
        return False

    phrase_history = list(trinity_voice.history) if trinity_voice else []
    if trinity_voice and trinity_voice.last_text:
        phrase_history.append(trinity_voice.last_text)

    # 1. Check against history
    for past_phrase in phrase_history:
        past_clean = (
            past_phrase.strip()
            .lower()
            .replace(".", "")
            .replace(",", "")
            .replace("!", "")
            .replace("?", "")
        )
        if not past_clean:
            continue

        ratio = SequenceMatcher(None, clean_text, past_clean).ratio()
        if ratio > 0.85 or clean_text in past_clean:
            logger.info(f"[STT] Echo detected: '{clean_text}' ~= '{past_clean}'")
            return True

    # 2. Noise heuristics
    if trinity_voice and (agent_was_speaking or (now - trinity_voice.last_speak_time < 3.0)):
        if confidence < 0.6 or (len(clean_text) < 5 and confidence < 0.8):
            logger.info(f"[STT] Noise detected: '{text}'")
            return True

    return False


def _handle_barge_in(text: str, confidence: float) -> bool:
    """Check for explicit stop commands and trigger barge-in."""
    trinity_voice = getattr(trinity, "voice", None)
    if not (trinity_voice and trinity_voice.is_speaking):
        return False

    stop_commands = {
        "стоп",
        "стій",
        "зупинись",
        "зупини",
        "тихо",
        "stop",
        "halt",
        "quiet",
        "wait",
    }
    clean_text = text.strip().lower()
    if any(cmd in clean_text for cmd in stop_commands) and confidence > 0.70:
        logger.info(f"[STT] 🛑 BARGE-IN DETECTED: '{text}'")
        trinity.stop()
        return True
    return False


@app.post("/api/stt/smart")
async def smart_speech_to_text(
    audio: UploadFile = File(...),
    previous_text: str = Form(default=""),
):
    """Smart STT with Full Duplex support (Barge-in)."""
    try:
        temp_file_path, suffix = await _prepare_audio_file(audio)
        wav_path = await _convert_to_wav(temp_file_path, suffix)

        # Smart analysis with context (async)
        result = await trinity.stt.transcribe_with_analysis(wav_path, previous_text=previous_text)

        is_echo_or_noise = _check_echo_and_noise(result.text, result.confidence, previous_text)
        if is_echo_or_noise:
            return {
                "text": "",
                "speech_type": "noise",
                "confidence": 0,
                "combined_text": previous_text,
                "should_send": False,
                "is_continuation": False,
                "ignored": True,
            }

        _handle_barge_in(result.text, result.confidence)

        if result.text:
            logger.info(
                f"[STT] Result: '{result.text}' (Type: {result.speech_type.value}, Conf: {result.confidence:.2f})",
            )

        # Clean up
        for path in {wav_path, temp_file_path}:
            if os.path.exists(path):
                os.unlink(path)

        return {
            "text": result.text,
            "speech_type": result.speech_type.value,
            "confidence": result.confidence,
            "combined_text": result.combined_text,
            "should_send": result.should_send,
            "is_continuation": result.is_continuation,
            "no_speech_prob": result.no_speech_prob,
        }

    except Exception as e:
        logger.error(f"Smart STT error: {e!s}")
        return {
            "text": "",
            "speech_type": "noise",
            "confidence": 0,
            "combined_text": previous_text,
            "should_send": False,
            "is_continuation": False,
            "ignored": True,
        }

    except Exception as e:
        logger.error(f"Smart STT error: {e!s}")
        # Don't crash client loop, return empty result
        return {
            "text": "",
            "speech_type": "noise",
            "confidence": 0,
            "combined_text": previous_text,
            "should_send": False,
            "is_continuation": False,
            "ignored": True,
        }


@app.post("/api/voice/transcribe")
async def transcribe_audio(file_path: str):
    """Transcribe a wav file"""
    result = await trinity.stt.transcribe_file(file_path)
    return {"text": result.text, "confidence": result.confidence}


# MCP Wrapper
class WhisperMCPServer:
    def __init__(self):
        # Local WhisperSTT instance for MCP wrapper

        self.stt = WhisperSTT()

    async def transcribe_audio(self, audio_path: str, language: str | None = "uk"):
        result = await self.stt.transcribe_file(audio_path, language)
        return {"text": result.text, "confidence": result.confidence}

    async def record_and_transcribe(self, duration: float = 5.0, language: str | None = None):
        result = await self.stt.record_and_transcribe(duration, language)
        return {"text": result.text, "confidence": result.confidence}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
