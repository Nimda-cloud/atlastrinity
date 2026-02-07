"""
Windsurf Proxy Server
=====================

OpenAI-compatible proxy that translates requests to Windsurf/Codeium Connect-RPC API.
Runs on port 8085 (same as copilot_proxy.py — use one or the other).

Usage:
  python scripts/windsurf_proxy.py                    # Default port 8085
  python scripts/windsurf_proxy.py --port 8086         # Custom port
  WINDSURF_API_KEY=sk-ws-... python scripts/windsurf_proxy.py

Environment:
  WINDSURF_API_KEY      - Required. Windsurf API key (sk-ws-...)
  WINDSURF_INSTALL_ID   - Optional. Installation ID from Windsurf DB
  WINDSURF_API_SERVER   - Optional. API server URL (default: https://server.self-serve.windsurf.com)
"""

from __future__ import annotations

import argparse
import http.client
import http.server
import json
import os
import re
import signal
import socketserver
import struct
import subprocess
import sys
import time
import uuid

# ─── Windsurf Free Models ────────────────────────────────────────────────────

WINDSURF_FREE_MODELS: dict[str, str] = {
    "deepseek-v3": "MODEL_DEEPSEEK_V3",
    "deepseek-r1": "MODEL_DEEPSEEK_R1",
    "swe-1": "MODEL_SWE_1",
    "swe-1.5": "MODEL_SWE_1_5",
    "grok-code-fast-1": "MODEL_GROK_CODE_FAST_1",
    "gpt-5.1-codex": "MODEL_PRIVATE_9",
    "gpt-5.1-codex-mini": "MODEL_PRIVATE_19",
    "gpt-5.1-codex-max-low": "MODEL_GPT_5_1_CODEX_MAX_LOW",
    "gpt-5.1-codex-low": "MODEL_GPT_5_1_CODEX_LOW",
    "gpt-5.1-codex-mini-low": "MODEL_GPT_5_1_CODEX_MINI_LOW",
    "kimi-k2.5": "kimi-k2-5",
}

ROLE_MAP = {"system": 0, "user": 1, "assistant": 2}

DEFAULT_API_SERVER = "https://server.self-serve.windsurf.com"
CHAT_ENDPOINT = "/exa.api_server_pb.ApiServerService/GetChatMessage"
LS_RAW_CHAT = "/exa.language_server_pb.LanguageServerService/RawGetChatMessage"
LS_HEARTBEAT = "/exa.language_server_pb.LanguageServerService/Heartbeat"

# ─── Language Server Auto-Detection ─────────────────────────────────────────


def detect_language_server() -> tuple[int, str]:
    """Detect running Windsurf language server port and CSRF token."""
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            if "language_server_macos_arm" not in line or "grep" in line:
                continue
            csrf = ""
            m = re.search(r"--csrf_token\s+(\S+)", line)
            if m:
                csrf = m.group(1)
            parts = line.split()
            if len(parts) >= 2:
                pid = parts[1]
                try:
                    lsof = subprocess.run(
                        ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-a", "-p", pid],
                        capture_output=True, text=True, timeout=5,
                    )
                    port = 0
                    for ll in lsof.stdout.splitlines():
                        if "LISTEN" in ll:
                            m2 = re.search(r":(\d+)\s+\(LISTEN\)", ll)
                            if m2:
                                c = int(m2.group(1))
                                if port == 0 or c < port:
                                    port = c
                    if port and csrf:
                        return port, csrf
                except Exception:
                    pass
            break
    except Exception:
        pass
    return 0, ""


def ls_heartbeat(port: int, csrf: str) -> bool:
    """Check if language server is alive."""
    import urllib.request
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}{LS_HEARTBEAT}",
            data=b"{}",
            headers={"Content-Type": "application/json", "x-codeium-csrf-token": csrf},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.getcode() == 200
    except Exception:
        return False


def log(msg: str) -> None:
    print(f"[WindsurfProxy] {msg}", file=sys.stderr, flush=True)


class WindsurfProxyHandler(http.server.BaseHTTPRequestHandler):
    processed_requests: int = 0
    start_time: float = 0.0

    def log_message(self, format, *args):
        # Suppress default access log, use our own
        pass

    def do_GET(self):
        WindsurfProxyHandler.processed_requests += 1

        if self.path in ["/v1/models", "/models"]:
            models_data = {
                "object": "list",
                "data": [
                    {
                        "id": model_name,
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "windsurf-free",
                    }
                    for model_name in WINDSURF_FREE_MODELS
                ],
            }
            self._send_json(200, models_data)

        elif self.path == "/v1/status":
            st = WindsurfProxyHandler.start_time
            uptime = time.time() - st if st else 0.0
            self._send_json(
                200,
                {
                    "uptime": uptime,
                    "processed_requests": WindsurfProxyHandler.processed_requests,
                    "provider": "windsurf",
                    "free_models": list(WINDSURF_FREE_MODELS.keys()),
                },
            )

        elif self.path in ["/health", "/v1/health"]:
            self._send_json(200, {"status": "ok", "provider": "windsurf"})

        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        WindsurfProxyHandler.processed_requests += 1

        if self.path not in ["/v1/chat/completions", "/chat/completions"]:
            self._send_json(404, {"error": f"Unknown endpoint: {self.path}"})
            return

        # Read request body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            request = json.loads(post_data)
        except Exception as e:
            log(f"Bad request: {e}")
            self._send_json(400, {"error": f"Invalid request: {e}"})
            return

        # Extract OpenAI-format fields
        model_name = request.get("model", "deepseek-v3")
        messages = request.get("messages", [])
        stream = request.get("stream", False)

        log(f"Request: model={model_name}, messages={len(messages)}, stream={stream}")

        # Resolve model ID
        model_id = WINDSURF_FREE_MODELS.get(model_name, model_name)
        if model_name not in WINDSURF_FREE_MODELS and not model_name.startswith("MODEL_"):
            log(f"Warning: model '{model_name}' not in free tier, using as-is")

        # Convert OpenAI messages to Windsurf format
        chat_messages = []
        for msg in messages:
            role = ROLE_MAP.get(msg.get("role", "user"), 1)
            content = msg.get("content", "")
            if isinstance(content, list):
                # Flatten multimodal content to text
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = " ".join(text_parts)
            chat_messages.append({"role": role, "content": content})

        # Build Connect-RPC payload
        api_key = os.environ.get("WINDSURF_API_KEY", "")
        install_id = os.environ.get("WINDSURF_INSTALL_ID", "")
        api_server = os.environ.get("WINDSURF_API_SERVER", DEFAULT_API_SERVER)

        if not api_key:
            self._send_json(500, {"error": "WINDSURF_API_KEY not set"})
            return

        windsurf_payload = json.dumps(
            {
                "chatMessages": chat_messages,
                "metadata": {
                    "ideName": "windsurf",
                    "ideVersion": "1.98.0",
                    "extensionVersion": "1.42.0",
                    "locale": "en",
                    "sessionId": f"proxy-{os.getpid()}",
                    "requestId": str(WindsurfProxyHandler.processed_requests),
                    "installationId": install_id,
                },
                "modelName": model_id,
            }
        ).encode()

        # Try local Language Server first, then fall back to cloud API
        ls_port = int(os.environ.get("WINDSURF_LS_PORT", "0"))
        ls_csrf = os.environ.get("WINDSURF_LS_CSRF", "")

        data = None
        use_ls = ls_port and ls_csrf

        if use_ls:
            try:
                # Build LS-specific payload with required fields
                now_rfc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                conv_id = str(uuid.uuid4())
                ls_messages = []
                for cm in chat_messages:
                    ls_messages.append({
                        **cm,
                        "messageId": str(uuid.uuid4()),
                        "timestamp": now_rfc,
                        "conversationId": conv_id,
                    })
                ls_body = json.dumps({
                    "chatMessages": ls_messages,
                    "metadata": {
                        "ideName": "windsurf",
                        "ideVersion": "1.98.0",
                        "extensionVersion": "1.42.0",
                        "locale": "en",
                        "sessionId": f"proxy-{os.getpid()}",
                        "requestId": str(WindsurfProxyHandler.processed_requests),
                        "installationId": install_id,
                        "apiKey": api_key,
                    },
                    "modelName": model_id,
                }).encode()
                envelope = struct.pack(">BI", 0, len(ls_body)) + ls_body

                conn = http.client.HTTPConnection("127.0.0.1", ls_port, timeout=300)
                conn.request(
                    "POST",
                    LS_RAW_CHAT,
                    envelope,
                    {
                        "Content-Type": "application/connect+json",
                        "Connect-Protocol-Version": "1",
                        "x-codeium-csrf-token": ls_csrf,
                    },
                )
                resp = conn.getresponse()
                data = resp.read()
                conn.close()
                log(f"Local LS response: {len(data)} bytes")
            except Exception as e:
                log(f"Local LS error: {e}, falling back to cloud API")
                data = None

        if data is None:
            # Fall back to direct cloud API
            try:
                host = api_server.replace("https://", "").replace("http://", "")
                conn = http.client.HTTPSConnection(host, timeout=300)
                conn.request(
                    "POST",
                    CHAT_ENDPOINT,
                    windsurf_payload,
                    {
                        "Content-Type": "application/connect+json",
                        "Connect-Protocol-Version": "1",
                        "Authorization": f"Basic {api_key}",
                    },
                )
                resp = conn.getresponse()
                data = resp.read()
                conn.close()
            except Exception as e:
                log(f"Upstream error: {e}")
                self._send_json(502, {"error": f"Upstream connection failed: {e}"})
                return

        # Parse Connect-RPC response
        try:
            result_text = self._parse_connect_rpc(data)
        except RuntimeError as e:
            log(f"Windsurf API error: {e}")
            self._send_json(502, {"error": str(e)})
            return

        # Convert to OpenAI-compatible response
        openai_response = {
            "id": f"ws-{WindsurfProxyHandler.processed_requests}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model_name,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result_text,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
        }

        if stream:
            # SSE streaming format
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            # Send content as a single chunk (Windsurf API doesn't support true streaming via REST)
            chunk = {
                "id": f"ws-{WindsurfProxyHandler.processed_requests}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": result_text},
                        "finish_reason": None,
                    }
                ],
            }
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())

            # Send finish chunk
            finish_chunk = {
                "id": f"ws-{WindsurfProxyHandler.processed_requests}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_name,
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop",
                    }
                ],
            }
            self.wfile.write(f"data: {json.dumps(finish_chunk)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
        else:
            log(f"Response: {len(result_text)} chars")
            self._send_json(200, openai_response)

    def _parse_connect_rpc(self, data: bytes) -> str:
        """Parse Connect-RPC framed response into text content."""
        if not data:
            raise RuntimeError("Empty response from Windsurf API")

        result_text = ""
        offset = 0
        while offset < len(data):
            if offset + 5 > len(data):
                break
            flag = data[offset]
            frame_len = int.from_bytes(data[offset + 1 : offset + 5], "big")
            frame_data = data[offset + 5 : offset + 5 + frame_len]
            offset += 5 + frame_len

            try:
                frame_json = json.loads(frame_data)
            except json.JSONDecodeError:
                continue

            if flag == 0x02:  # Error/trailer frame
                error_info = frame_json.get("error", {})
                error_code = error_info.get("code", "unknown")
                error_msg = error_info.get("message", "Unknown error")
                raise RuntimeError(f"Windsurf API ({error_code}): {error_msg}")

            # Data frame — extract content
            if "text" in frame_json:
                result_text += frame_json["text"]
            elif "content" in frame_json:
                result_text += frame_json["content"]
            elif "chatMessage" in frame_json:
                result_text += frame_json["chatMessage"].get("content", "")

        if not result_text:
            raise RuntimeError("No content in Windsurf API response")

        return result_text

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(port: int = 8085) -> None:
    api_key = os.environ.get("WINDSURF_API_KEY", "")
    if not api_key:
        log("ERROR: WINDSURF_API_KEY environment variable not set!")
        log("Run: python tools/get_windsurf_token.py --key-only")
        sys.exit(1)

    log(f"API Key: {api_key[:15]}...{api_key[-8:]}")
    log(f"Free models: {', '.join(sorted(WINDSURF_FREE_MODELS.keys()))}")

    # Auto-detect local Language Server
    ls_port = int(os.environ.get("WINDSURF_LS_PORT", "0"))
    ls_csrf = os.environ.get("WINDSURF_LS_CSRF", "")
    if not ls_port or not ls_csrf:
        detected_port, detected_csrf = detect_language_server()
        if detected_port and detected_csrf:
            ls_port = detected_port
            ls_csrf = detected_csrf
            os.environ["WINDSURF_LS_PORT"] = str(ls_port)
            os.environ["WINDSURF_LS_CSRF"] = ls_csrf
    if ls_port and ls_csrf and ls_heartbeat(ls_port, ls_csrf):
        log(f"Local LS detected: port={ls_port}, csrf={ls_csrf[:20]}...")
    else:
        log("Local LS not detected, using cloud API only")

    WindsurfProxyHandler.start_time = time.time()
    server_address = ("127.0.0.1", port)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(server_address, WindsurfProxyHandler)
    log(f"Serving at http://127.0.0.1:{port}")
    log(f"OpenAI-compatible endpoint: http://127.0.0.1:{port}/v1/chat/completions")

    def shutdown_handler(signum, frame):
        log("Shutting down proxy...")
        httpd.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Windsurf OpenAI-compatible proxy")
    parser.add_argument("--port", type=int, default=8085, help="Port to listen on (default: 8085)")
    args = parser.parse_args()
    run(port=args.port)
