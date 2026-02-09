"""
Universal LLM Proxy Server
==========================

OpenAI-compatible proxy that routes requests to the appropriate LLM provider
based on the model name or provider configuration.

Supports:
- GitHub Copilot (ghu_ token) → api.githubcopilot.com
- Windsurf/Codeium (sk-ws- token) → server.self-serve.windsurf.com

Provider selection:
1. Model name mapping (e.g., deepseek-* → windsurf, gpt-* → copilot)
2. Provider header (X-Provider: copilot|windsurf)
3. Default provider from environment (LLM_PROVIDER)

Usage:
  python scripts/universal_proxy.py                    # Default port 8085
  python scripts/universal_proxy.py --port 8086      # Custom port
  LLM_PROVIDER=windsurf python scripts/universal_proxy.py  # Force provider

Environment:
  COPILOT_API_KEY        - GitHub Copilot ghu_ token
  WINDSURF_API_KEY       - Windsurf sk-ws- token
  WINDSURF_INSTALL_ID   - Installation ID from Windsurf DB
  LLM_PROVIDER          - Default provider (copilot|windsurf)
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import signal
import socketserver
import sys
import time
import uuid
from urllib.request import Request, urlopen

# ─── Provider Configuration ───────────────────────────────────────────────────

# Model name patterns for provider detection
COPILOT_MODEL_PATTERNS = [
    "gpt-4o",
    "gpt-4.1",
    "gpt-4o-mini",
    "gpt-5-mini",
    "grok-code-fast-1",
    "oswe-vscode-secondary",
    "claude-3.5-sonnet",
    "o3-mini",
    "raptor-mini",
]

WINDSURF_MODEL_PATTERNS = [
    # Windsurf-only models (used for auto-detection of provider)
    "windsurf-fast",
    "swe-1",
    "swe-1.5",
    # Free / unlimited Windsurf models
    "deepseek-v3",
    "deepseek-r1",
    "grok-code-fast-1",
    "kimi-k2.5",
]

# Windsurf internal model mapping (synced with providers/windsurf.py WINDSURF_MODELS)
WINDSURF_MODEL_MAPPING = {
    # Premium models (use Cascade message quota)
    "claude-4.5-opus": "MODEL_CLAUDE_4_5_OPUS",
    "claude-4-sonnet": "MODEL_CLAUDE_4_SONNET",
    "claude-4.5-sonnet": "MODEL_PRIVATE_2",
    "claude-haiku-4.5": "MODEL_PRIVATE_11",
    "gpt-4.1": "MODEL_CHAT_GPT_4_1_2025_04_14",
    "gpt-5.1": "MODEL_PRIVATE_12",
    "swe-1.5": "MODEL_SWE_1_5",
    "windsurf-fast": "MODEL_CHAT_11121",
    # Free / unlimited models
    "deepseek-v3": "MODEL_DEEPSEEK_V3",
    "deepseek-r1": "MODEL_DEEPSEEK_R1",
    "swe-1": "MODEL_SWE_1",
    "grok-code-fast-1": "MODEL_GROK_CODE_FAST_1",
    "kimi-k2.5": "kimi-k2-5",
}

# Default ports
DEFAULT_PORT = 8085


# Windsurf Session State
class WindsurfState:
    session_id: str = str(uuid.uuid4())
    request_count: int = 0


# ─── Colors ──────────────────────────────────────────────────────────────────


class C:
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def log(msg: str) -> None:
    print(f"[UniversalProxy] {msg}", file=sys.stderr, flush=True)


def info(msg: str) -> None:
    print(f"{C.GREEN}✓{C.RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{C.YELLOW}⚠{C.RESET} {msg}")


def error(msg: str) -> None:
    print(f"{C.RED}✗{C.RESET} {msg}")


# ─── Provider Detection ─────────────────────────────────────────────────────


def detect_provider(model_name: str, provider_header: str | None = None) -> str:
    """Detect which provider should handle the request."""
    # 1. Explicit provider header
    if provider_header:
        provider = provider_header.lower()
        if provider in ("copilot", "windsurf"):
            return provider

    # 2. Model name patterns
    model_lower = model_name.lower()

    # Check Windsurf patterns first (more specific)
    for pattern in WINDSURF_MODEL_PATTERNS:
        if pattern in model_lower:
            return "windsurf"

    # Check Copilot patterns
    for pattern in COPILOT_MODEL_PATTERNS:
        if pattern in model_lower:
            return "copilot"

    # 3. Environment default
    env_provider = os.getenv("LLM_PROVIDER", "").lower()
    if env_provider in ("copilot", "windsurf"):
        return env_provider

    # 4. Default fallback
    return "copilot"


# ─── Copilot Handler ───────────────────────────────────────────────────────────


def handle_copilot_request(
    method: str, path: str, headers: dict, body: bytes
) -> tuple[int, dict, bytes]:
    """Handle request by forwarding to GitHub Copilot API."""
    # log(f"DEBUG: handle_copilot_request path={path}")
    copilot_key = os.getenv("COPILOT_API_KEY")
    if not copilot_key:
        error("COPILOT_API_KEY not set")
        return 500, {"error": "COPILOT_API_KEY not set"}, b"COPILOT_API_KEY not set"

    try:
        # Get session token
        # log("DEBUG: Fetching Copilot session token...")
        token_headers = {
            "Authorization": f"token {copilot_key}",
            "Editor-Version": "vscode/1.85.0",
            "Editor-Plugin-Version": "copilot/1.144.0",
            "User-Agent": "GithubCopilot/1.144.0",
            "Accept": "application/json",
        }
        token_req = Request(
            "https://api.github.com/copilot_internal/v2/token",
            headers=token_headers,
        )
        with urlopen(token_req, timeout=30) as resp:
            token_data = json.loads(resp.read().decode())
            session_token = token_data.get("token")
            # Use api.githubcopilot.com as it's more reliable for internal routing
            api_endpoint = "https://api.githubcopilot.com"
            # log(f"DEBUG: Token acquired. Using endpoint: {api_endpoint}")

        if not session_token:
            error("Failed to get Copilot session token")
            return 500, {"error": "Failed to get session token"}, b"Failed to get session token"

        # Forward request to Copilot API
        if path.startswith("/v1/"):
            path = path.replace("/v1/", "/")

        copilot_headers = {
            "Authorization": f"Bearer {session_token}",
            "Content-Type": "application/json",
            "Editor-Version": "vscode/1.85.0",
        }

        # Add any additional headers from original request
        copilot_headers.update(
            {
                key: value
                for key, value in headers.items()
                if key.lower()
                not in [
                    "authorization",
                    "accept",
                    "content-type",
                    "user-agent",
                    "editor-version",
                    "editor-plugin-version",
                    "copilot-vision-request",
                ]
            }
        )

        url = f"{api_endpoint}{path}"
        # log(f"DEBUG: Forwarding request to {url}")
        req = Request(url, data=body, headers=copilot_headers, method=method)
        # Increased timeout to 600 for high-reasoning models (Raptor)
        with urlopen(req, timeout=600) as resp:
            status_code = resp.getcode()
            response_body = resp.read()
            response_headers = dict(resp.headers)
            # log(f"DEBUG: Received response {status_code}, length {len(response_body)}")

            # Filter headers to send back
            allowed_headers = [
                "content-type",
                "date",
                "x-request-id",
                "x-github-request-id",
                "cache-control",
                "etag",
            ]
            filtered_headers = {
                k: v for k, v in response_headers.items() if k.lower() in allowed_headers
            }

            return status_code, filtered_headers, response_body

    except Exception as e:
        import traceback

        error(f"Copilot request failed: {e}")
        traceback.print_exc()
        return 502, {"error": f"Copilot request failed: {e}"}, str(e).encode()


# ─── Windsurf Handler ───────────────────────────────────────────────────────────


def handle_windsurf_request(
    method: str, path: str, headers: dict, body: bytes
) -> tuple[int, dict, bytes]:
    """Handle request by forwarding to Windsurf Connect-RPC API."""
    api_key = os.getenv("WINDSURF_API_KEY")
    install_id = os.getenv("WINDSURF_INSTALL_ID", "")
    api_server = os.getenv("WINDSURF_API_SERVER", "https://server.self-serve.windsurf.com")

    WindsurfState.request_count += 1
    session_id = WindsurfState.session_id
    request_id = str(WindsurfState.request_count)

    if not api_key:
        error("WINDSURF_API_KEY not set")
        return 500, {"error": "WINDSURF_API_KEY not set"}, b"WINDSURF_API_KEY not set"

    try:
        # Parse OpenAI request
        if body:
            request_data = json.loads(body.decode())
        else:
            request_data = {}

        model_name = request_data.get("model", "deepseek-v3")
        messages = request_data.get("messages", [])
        _ = request_data.get("stream", False)  # stream not used in current implementation

        # Convert OpenAI messages to Windsurf format
        chat_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = 1  # Default to user
            role_type = msg.get("role")
            if role_type == "system":
                role = 0
            elif role_type == "assistant":
                role = 2

            content = msg.get("content", "")
            if isinstance(content, list):
                # Flatten multimodal content to text
                text_parts: list[str] = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        val = item.get("text")
                        if isinstance(val, str):
                            text_parts.append(val)
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = " ".join(text_parts)

            chat_messages.append({"role": role, "content": str(content)})

        # Build Connect-RPC payload
        windsurf_payload = json.dumps(
            {
                "chatMessages": chat_messages,
                "metadata": {
                    "ideName": "windsurf",
                    "ideVersion": "1.98.0",
                    "extensionVersion": "1.42.0",
                    "locale": "en",
                    "sessionId": session_id,
                    "requestId": request_id,
                    "installationId": install_id,
                },
                "modelName": WINDSURF_MODEL_MAPPING.get(model_name, model_name),
            }
        ).encode()

        # Send to Windsurf API
        windsurf_headers = {
            "Content-Type": "application/connect+json",
            "Connect-Protocol-Version": "1",
            "Authorization": f"Basic {api_key}",
            "User-Agent": "Windsurf/1.98.0",
            "X-Client-IDE": "windsurf",
            "X-Request-Id": request_id,
        }

        url = f"{api_server}/exa.api_server_pb.ApiServerService/GetChatMessage"
        req = Request(url, data=windsurf_payload, headers=windsurf_headers, method=method)

        with urlopen(req, timeout=300) as resp:
            response_data = resp.read()

            # Parse Connect-RPC response
            result_chunks: list[str] = []
            offset = 0
            while offset < len(response_data):
                if offset + 5 > len(response_data):
                    break
                flag = response_data[offset]
                frame_len = int.from_bytes(response_data[offset + 1 : offset + 5], "big")
                frame_data = response_data[offset + 5 : offset + 5 + frame_len]
                offset += 5 + frame_len

                try:
                    frame_json = json.loads(frame_data)
                except json.JSONDecodeError:
                    continue

                if flag == 0x02:  # Error frame
                    error_info = frame_json.get("error", {})
                    error_code = error_info.get("code", "unknown")
                    error_msg = error_info.get("message", "Unknown error")
                    return (
                        502,
                        {"error": f"Windsurf API ({error_code}): {error_msg}"},
                        str(error_info).encode(),
                    )

                # Data frame
                if isinstance(frame_json, dict):
                    if "text" in frame_json:
                        val = frame_json.get("text")
                        if isinstance(val, str):
                            result_chunks.append(val)
                    elif "content" in frame_json:
                        val = frame_json.get("content")
                        if isinstance(val, str):
                            result_chunks.append(val)
                    elif "chatMessage" in frame_json:
                        msg_obj = frame_json.get("chatMessage")
                        if isinstance(msg_obj, dict):
                            val = msg_obj.get("content")
                            if isinstance(val, str):
                                result_chunks.append(val)

            result_text = "".join(result_chunks)

        # Convert to OpenAI-compatible response
        openai_response = {
            "id": f"ws-{int(time.time())}",
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

        response_body = json.dumps(openai_response).encode()
        response_headers = {"Content-Type": "application/json"}

        return resp.getcode(), response_headers, response_body

    except Exception as e:
        error(f"Windsurf request failed: {e}")
        return 502, {"error": f"Windsurf request failed: {e}"}, str(e).encode()


# ─── Proxy Server ───────────────────────────────────────────────────────────────


class UniversalProxyHandler(http.server.BaseHTTPRequestHandler):
    processed_requests: int = 0
    start_time: float = 0.0

    def log_message(self, format, *args):
        # Suppress default access log
        pass

    def do_GET(self):
        UniversalProxyHandler.processed_requests += 1

        if self.path in ["/v1/models", "/models"]:
            # Return combined model list from both providers
            models_data = {
                "object": "list",
                "data": [
                    # Copilot models
                    {
                        "id": "gpt-4o",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "github-copilot",
                    },
                    {
                        "id": "gpt-4.1",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "github-copilot",
                    },
                    {
                        "id": "gpt-4o-mini",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "github-copilot",
                    },
                    {
                        "id": "gpt-5-mini",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "github-copilot",
                    },
                    {
                        "id": "grok-code-fast-1",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "github-copilot",
                    },
                    {
                        "id": "oswe-vscode-secondary",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "github-copilot",
                    },
                    {
                        "id": "claude-3.5-sonnet",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "github-copilot",
                    },
                    {
                        "id": "o3-mini",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "github-copilot",
                    },
                    # Windsurf models
                    {
                        "id": "deepseek-v3",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "windsurf-free",
                    },
                    {
                        "id": "deepseek-r1",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "windsurf-free",
                    },
                    {
                        "id": "swe-1",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "windsurf-free",
                    },
                    {
                        "id": "swe-1.5",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "windsurf-free",
                    },
                    {
                        "id": "kimi-k2.5",
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "windsurf-free",
                    },
                ],
            }
            self._send_json(200, models_data)

        elif self.path == "/v1/status":
            st = UniversalProxyHandler.start_time
            uptime = time.time() - st if st else 0.0
            self._send_json(
                200,
                {
                    "uptime": uptime,
                    "processed_requests": UniversalProxyHandler.processed_requests,
                    "provider": "universal",
                    "supported_providers": ["copilot", "windsurf"],
                    "default_provider": os.getenv("LLM_PROVIDER", "copilot"),
                },
            )

        elif self.path in ["/health", "/v1/health"]:
            self._send_json(200, {"status": "ok", "provider": "universal"})

        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        UniversalProxyHandler.processed_requests += 1

        if self.path not in ["/v1/chat/completions", "/chat/completions"]:
            self._send_json(404, {"error": f"Unknown endpoint: {self.path}"})
            return

        # Read request body
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            # Parse request for model detection
            request_data = json.loads(body)
            model_name = request_data.get("model", "gpt-4o")
            provider_header = self.headers.get("X-Provider")

            # Detect which provider to use
            provider = detect_provider(model_name, provider_header)

            log(f"Request: model={model_name}, provider={provider}")

            # Route to appropriate handler
            if provider == "windsurf":
                status, headers, response_body = handle_windsurf_request(
                    "POST", self.path, dict(self.headers), body
                )
            else:  # Default to copilot
                status, headers, response_body = handle_copilot_request(
                    "POST", self.path, dict(self.headers), body
                )

            # Send response
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(response_body)

        except Exception as e:
            log(f"Request error: {e}")
            self._send_json(500, {"error": f"Request error: {e}"})

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(port: int = DEFAULT_PORT) -> None:
    # Check environment
    copilot_key = os.getenv("COPILOT_API_KEY")
    windsurf_key = os.getenv("WINDSURF_API_KEY")

    log(f"Starting Universal LLM Proxy on port {port}")

    def mask_key(k: str | None) -> str:
        if not k or not isinstance(k, str):
            return "NOT SET"
        if len(k) < 15:
            return k
        return k[:15] + "..." + k[-8:]  # type: ignore

    if copilot_key:
        info(f"Copilot API key: {mask_key(copilot_key)}")
    else:
        warn("COPILOT_API_KEY not set (Copilot requests will fail)")

    if windsurf_key:
        info(f"Windsurf API key: {mask_key(windsurf_key)}")
    else:
        warn("WINDSURF_API_KEY not set (Windsurf requests will fail)")

    default_provider = os.getenv("LLM_PROVIDER", "copilot")
    info(f"Default provider: {default_provider}")

    UniversalProxyHandler.start_time = time.time()
    server_address = ("127.0.0.1", port)

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = ReusableTCPServer(server_address, UniversalProxyHandler)

    log(f"Serving at http://127.0.0.1:{port}")
    log(f"OpenAI-compatible endpoint: http://127.0.0.1:{port}/v1/chat/completions")
    log(f"Models list: http://127.0.0.1:{port}/v1/models")

    _shutting_down = False

    def shutdown_handler(signum, frame):
        nonlocal _shutting_down
        if _shutting_down:
            return
        _shutting_down = True
        log("Shutting down proxy...")
        httpd.server_close()
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    httpd.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Universal LLM Proxy — routes requests to Copilot or Windsurf based on model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Default port 8085
  %(prog)s --port 8086               # Custom port
  LLM_PROVIDER=windsurf %(prog)s     # Force Windsurf provider
        """,
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to listen on")
    args = parser.parse_args()
    run(port=args.port)
