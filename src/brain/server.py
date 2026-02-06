"""AtlasTrinity Brain Server
Exposes the orchestrator via FastAPI for Electron IPC with monitoring integration
"""

import os
import time
import warnings

# Suppress common third-party warnings
warnings.filterwarnings("ignore", category=UserWarning, module="espnet2.torch_utils.device_funcs")
# Suppress PyTorch and ESPnet warnings triggered by ukrainian-tts
warnings.filterwarnings("ignore", message=".*torch.nn.utils.weight_norm is deprecated.*")
warnings.filterwarnings(
    "ignore", message=".*make_pad_mask with a list of lengths is not tracable.*"
)

import sys

# Force UTF-8 encoding for stdout/stderr to support Ukrainian characters in terminal
if sys.stdout.encoding != "utf-8":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Import CONFIG_ROOT before using it
from .config_loader import config
from .services_manager import ServiceStatus

# Step 1: Ensure core system services (Redis, Docker) are running
# We'll run this in the background to avoid blocking server binding

# Set API keys as environment variables for internal libraries
copilot_key = config.get_api_key("copilot_api_key")
github_token = config.get_api_key("github_token")

if copilot_key:
    os.environ["COPILOT_API_KEY"] = copilot_key
    print("[Server] ✓ COPILOT_API_KEY loaded from global context", file=sys.stderr)
if github_token:
    os.environ["GITHUB_TOKEN"] = github_token
    print("[Server] ✓ GITHUB_TOKEN loaded from global context", file=sys.stderr)

import asyncio
from typing import Any, cast

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .logger import logger
from .mcp_manager import mcp_manager
from .orchestrator import Trinity
from .production_setup import run_production_setup
from .voice.stt import WhisperSTT

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
        from .monitoring import get_monitoring_system

        monitoring_system = get_monitoring_system()
        monitoring_system.log_for_grafana("Server startup initiated", level="info")
    except ImportError:
        logger.warning("Monitoring system not available")

    # Initialize services in background (handled by startup workflow)
    # asyncio.create_task(ensure_all_services())

    # Initialize components
    await trinity.initialize()

    # Start Process Watchdog
    try:
        from .watchdog import watchdog

        await watchdog.start()
        logger.info("[Server] Process Watchdog started")
    except Exception as e:
        logger.error(f"[Server] Failed to start watchdog: {e}")

    # Start stdin watchdog to ensure we die when parent dies
    def stdin_watchdog_loop():
        try:
            sys.stdin.read()
        except EOFError:
            pass
        logger.info("[Server] Parent process disconnected (stdin EOF), shutting down...")
        import os

        os._exit(0)

    import threading

    threading.Thread(target=stdin_watchdog_loop, daemon=True).start()

    # Production: copy configs from Resources/ to ~/.config/ if needed
    run_production_setup()

    yield
    # Shutdown
    logger.info("AtlasTrinity Brain is going to sleep...")

    # Shutdown monitoring
    try:
        from .monitoring import get_monitoring_system

        monitoring_system = get_monitoring_system()
        monitoring_system.log_for_grafana("Server shutdown initiated", level="info")
    except ImportError:
        pass

    # Clean shutdown of orchestrator
    try:
        await asyncio.wait_for(trinity.shutdown(), timeout=5.0)
    except TimeoutError:
        logger.warning("Trinity shutdown timed out, forcing...")
    except Exception as e:
        logger.error(f"Error during trinity shutdown: {e}")


app = FastAPI(title="AtlasTrinity Brain", lifespan=lifespan)

# CORS setup for Electron
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
async def chat(
    request: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    background_tasks: BackgroundTasks = None,  # type: ignore
):
    """Send a user request to the system with monitoring and file support"""
    from .services.file_processor import FileProcessor

    if current_task and not current_task.done():
        raise HTTPException(status_code=409, detail="System is busy")

    # Process files if any
    file_info = {"text": "", "images": []}
    if files:
        logger.info(f"[SERVER] Processing {len(files)} uploaded files...")
        file_info = await FileProcessor.process_files(files)
        logger.info("[SERVER] File processing complete.")

    file_context = cast(str, file_info.get("text", ""))
    images = cast(list[dict[str, Any]], file_info.get("images", []))

    # Combine request with file context
    full_request = request
    if file_context:
        full_request = f"{request}\n\n{file_context}"

    print(f"[SERVER] Received request: {full_request[:100]}...", file=sys.stderr)  # Log truncated
    logger.info(f"Received request: {full_request[:200]}...")

    # Start monitoring for this request
    start_time = time.time()
    try:
        from .monitoring import get_monitoring_system

        monitoring_system = get_monitoring_system()
        monitoring_system.start_request()
        monitoring_system.log_for_grafana(
            f"Chat request started: {request[:50]}...", level="info", request_type="chat"
        )
    except ImportError:
        pass

    # Run orchestration in background/loop
    try:
        # Pass the FULL request including file content and images to Trinity
        result = await trinity.run(full_request, images=images)

        # Record successful request
        request_duration = time.time() - start_time
        try:
            from .monitoring import get_monitoring_system

            monitoring_system = get_monitoring_system()
            monitoring_system.record_request("chat", "success", request_duration)
            monitoring_system.log_for_grafana(
                "Chat request completed",
                level="info",
                request_type="chat",
                duration=request_duration,
                status="success",
            )
        except ImportError:
            pass

        return {"status": "completed", "result": result}
    except asyncio.CancelledError:
        logger.info("Request interrupted/cancelled")

        # Record cancelled request
        request_duration = time.time() - start_time
        try:
            from .monitoring import get_monitoring_system

            monitoring_system = get_monitoring_system()
            monitoring_system.record_request("chat", "cancelled", request_duration)
            monitoring_system.log_for_grafana(
                "Chat request cancelled",
                level="warning",
                request_type="chat",
                duration=request_duration,
                status="cancelled",
            )
        except ImportError:
            pass

        return {"status": "interrupted", "detail": "Task was cancelled by a new request"}
    except Exception as e:
        logger.exception(f"Error processing request: {request[:50]}...")

        # Record failed request
        request_duration = time.time() - start_time
        try:
            from .monitoring import get_monitoring_system

            monitoring_system = get_monitoring_system()
            monitoring_system.record_request("chat", "error", request_duration)
            monitoring_system.log_for_grafana(
                "Chat request failed",
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
            from .monitoring import get_monitoring_system

            monitoring_system = get_monitoring_system()
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
        from .monitoring import get_monitoring_system

        monitoring_system = get_monitoring_system()
        metrics = monitoring_system.get_metrics_snapshot()

        # Add system health status
        metrics["monitoring_health"] = monitoring_system.is_healthy()

        return {"status": "success", "data": metrics}
    except ImportError:
        return {"status": "error", "message": "Monitoring system not available"}
    except Exception as e:
        logger.error(f"Error getting monitoring metrics: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/monitoring/processes")
async def get_processes():
    """Get status of all tracked processes from Watchdog."""
    try:
        from .watchdog import watchdog

        return {"status": "success", "data": watchdog.get_status()}
    except Exception as e:
        logger.error(f"Error getting process status: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/monitoring/health")
async def monitoring_health():
    """Check monitoring system health"""
    try:
        from .monitoring import get_monitoring_system

        monitoring_system = get_monitoring_system()
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
        "система стоп",
        "зупини систему",
        "атлас стоп",
        "атлас тиша",
        "вимкни звук",
        "system stop",
        "atlas stop",
        "stop system",
        "silence mode",
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


# =============================================================================
# Google Maps API Endpoints
# =============================================================================

from .map_state import map_state_manager


@app.post("/api/maps/search")
async def maps_search(payload: dict[str, Any]):
    """
    Search for places using Google Maps MCP
    Payload: {query: str, location?: str, radius?: int}
    """
    try:
        query = payload.get("query")
        location = payload.get("location")
        radius = payload.get("radius", 1000)

        if not query:
            raise HTTPException(status_code=400, detail="query is required")

        # Call MCP googlemaps tool
        result = await mcp_manager.call_tool(
            "googlemaps",
            "maps_search_places",
            {"query": query, "location": location, "radius": radius},
        )

        # Parse result and add markers
        map_state_manager.clear_markers()

        if isinstance(result, dict) and "places" in result:
            places = result["places"]
            for place in places[:20]:  # Limit to 20 markers
                position = place.get("location", {})
                if "lat" in position and "lng" in position:
                    marker_type = _categorize_place(place.get("types", []))
                    map_state_manager.add_marker(
                        position=position,
                        title=place.get("name", "Unknown"),
                        marker_type=marker_type,
                        data=place,
                    )

            # Center on first result
            if places and "location" in places[0]:
                loc = places[0]["location"]
                map_state_manager.set_center(loc["lat"], loc["lng"], 14)

        return {"status": "success", "data": result, "map_state": map_state_manager.to_dict()}

    except Exception as e:
        logger.exception(f"Maps search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/maps/directions")
async def maps_directions(payload: dict[str, Any]):
    """
    Get directions between two points
    Payload: {origin: str, destination: str, mode?: str}
    """
    try:
        origin = payload.get("origin")
        destination = payload.get("destination")
        mode = payload.get("mode", "driving")

        if not origin or not destination:
            raise HTTPException(status_code=400, detail="origin and destination are required")

        # Call MCP googlemaps tool
        result = await mcp_manager.call_tool(
            "googlemaps",
            "maps_directions",
            {"origin": origin, "destination": destination, "mode": mode},
        )

        # Parse result and add route
        map_state_manager.clear_routes()

        if isinstance(result, dict) and "routes" in result:
            routes = result["routes"]
            if routes:
                route_data = routes[0]
                legs = route_data.get("legs", [])
                if legs:
                    leg = legs[0]
                    map_state_manager.add_route(
                        origin=leg.get("start_location", {}),
                        destination=leg.get("end_location", {}),
                        polyline=route_data.get("overview_polyline", {}).get("points", ""),
                        distance=leg.get("distance", {}).get("text", "Unknown"),
                        duration=leg.get("duration", {}).get("text", "Unknown"),
                        steps=leg.get("steps", []),
                        mode=mode,
                    )

                    # Add origin/destination markers
                    start_loc = leg.get("start_location", {})
                    end_loc = leg.get("end_location", {})
                    if start_loc.get("lat") and start_loc.get("lng"):
                        map_state_manager.add_marker(
                            position=start_loc,
                            title=origin,
                            marker_type="origin",
                            color="#00ff00",
                        )
                    if end_loc.get("lat") and end_loc.get("lng"):
                        map_state_manager.add_marker(
                            position=end_loc,
                            title=destination,
                            marker_type="destination",
                            color="#ff0000",
                        )

                    # Center on route
                    if start_loc.get("lat") and start_loc.get("lng"):
                        map_state_manager.set_center(start_loc["lat"], start_loc["lng"], 13)

        return {"status": "success", "data": result, "map_state": map_state_manager.to_dict()}

    except Exception as e:
        logger.exception(f"Maps directions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/maps/place-details")
async def maps_place_details(payload: dict[str, Any]):
    """
    Get detailed information about a place
    Payload: {place_id: str}
    """
    try:
        place_id = payload.get("place_id")
        if not place_id:
            raise HTTPException(status_code=400, detail="place_id is required")

        result = await mcp_manager.call_tool(
            "googlemaps", "maps_place_details", {"place_id": place_id}
        )

        # Set as active place
        if isinstance(result, dict):
            map_state_manager.set_active_place(result)

        return {"status": "success", "data": result}

    except Exception as e:
        logger.exception(f"Maps place details error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/maps/street-view")
async def maps_street_view(payload: dict[str, Any]):
    """
    Get Street View image
    Payload: {location: str, heading?: int, pitch?: int, fov?: int, cyberpunk?: bool}
    """
    try:
        location = payload.get("location")
        if not location:
            raise HTTPException(status_code=400, detail="location is required")

        heading = payload.get("heading", 0)
        pitch = payload.get("pitch", 0)
        fov = payload.get("fov", 90)
        cyberpunk = payload.get("cyberpunk", True)

        result = await mcp_manager.call_tool(
            "googlemaps",
            "maps_street_view",
            {
                "location": location,
                "heading": heading,
                "pitch": pitch,
                "fov": fov,
                "cyberpunk": cyberpunk,
            },
        )

        return {"status": "success", "data": result}

    except Exception as e:
        logger.exception(f"Maps street view error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/maps/state")
async def get_map_state():
    """Get current map state (markers, routes, center, etc.)"""
    try:
        return {"status": "success", "data": map_state_manager.to_dict()}
    except Exception as e:
        logger.exception(f"Maps state error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/maps/clear")
async def clear_map():
    """Clear all markers and routes"""
    try:
        map_state_manager.clear_all()
        return {"status": "success", "message": "Map cleared"}
    except Exception as e:
        logger.exception(f"Maps clear error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _categorize_place(types: list[str]) -> str:
    """Categorize a place based on Google Maps types"""
    if not types:
        return "custom"

    # Priority-based categorization
    if any(t in types for t in ["restaurant", "cafe", "bar", "food"]):
        return "restaurant"
    elif any(t in types for t in ["lodging", "hotel"]):
        return "hotel"
    elif any(
        t in types
        for t in ["tourist_attraction", "museum", "park", "point_of_interest", "landmark"]
    ):
        return "attraction"
    else:
        return "custom"


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

    uvicorn.run(app, host="0.0.0.0", port=8000)
