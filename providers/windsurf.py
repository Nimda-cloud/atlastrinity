import json
import os
import sys
from collections.abc import Callable
from typing import Any

import httpx
import requests
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult

# Type aliases
ContentItem = str | dict[str, Any]

# ─── Windsurf Free Models ────────────────────────────────────────────────────
# Only FREE tier models from Windsurf/Codeium
# These do not consume premium credits

WINDSURF_FREE_MODELS: dict[str, str] = {
    # Display name -> Windsurf internal model ID
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

# Default free model
WINDSURF_DEFAULT_MODEL = "deepseek-v3"

# Windsurf Connect-RPC role mapping
ROLE_SYSTEM = 0
ROLE_USER = 1
ROLE_ASSISTANT = 2


class WindsurfLLM(BaseChatModel):
    """Windsurf/Codeium LLM provider.

    Supports two modes:
    1. Proxy mode (default): Sends OpenAI-compatible requests to a local proxy
       (windsurf_proxy.py on port 8085) which translates to Windsurf Connect-RPC API.
    2. Direct mode: Sends Connect-RPC requests directly to Windsurf API server.

    Only FREE tier models are available to avoid premium credit consumption.

    Environment variables:
        WINDSURF_API_KEY     - Windsurf API key (sk-ws-...)
        WINDSURF_MODEL       - Default model name
        WINDSURF_PROXY_URL   - Proxy URL (default: http://127.0.0.1:8085)
        WINDSURF_DIRECT      - Set to "true" to bypass proxy and call API directly
        WINDSURF_INSTALL_ID  - Installation ID (from Windsurf DB)
        WINDSURF_API_SERVER  - API server URL (default: https://server.self-serve.windsurf.com)
    """

    model_name: str | None = None
    api_key: str | None = None
    max_tokens: int = 4096
    proxy_url: str = "http://127.0.0.1:8085"
    direct_mode: bool = False
    api_server: str = "https://server.self-serve.windsurf.com"
    installation_id: str = ""
    _tools: list[Any] | None = None

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        max_tokens: int | None = None,
        proxy_url: str | None = None,
        direct_mode: bool | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        # Model
        self.model_name = model_name or os.getenv("WINDSURF_MODEL", WINDSURF_DEFAULT_MODEL)

        # Validate model is in free tier
        if self.model_name not in WINDSURF_FREE_MODELS:
            available = ", ".join(sorted(WINDSURF_FREE_MODELS.keys()))
            raise ValueError(
                f"WindsurfLLM: Model '{self.model_name}' is not in the FREE tier. "
                f"Available free models: {available}"
            )

        self.max_tokens = max_tokens or 4096

        # API key
        ws_key = api_key or os.getenv("WINDSURF_API_KEY")
        if not ws_key:
            raise RuntimeError(
                "WINDSURF_API_KEY environment variable must be set. "
                "Run: python tools/get_windsurf_token.py --key-only"
            )
        self.api_key = ws_key

        # Mode: proxy or direct
        self.direct_mode = (
            direct_mode
            if direct_mode is not None
            else (os.getenv("WINDSURF_DIRECT", "").lower() == "true")
        )

        # Proxy URL
        self.proxy_url = proxy_url or os.getenv("WINDSURF_PROXY_URL", "http://127.0.0.1:8085")

        # Direct mode settings
        self.api_server = os.getenv("WINDSURF_API_SERVER", "https://server.self-serve.windsurf.com")
        self.installation_id = os.getenv("WINDSURF_INSTALL_ID", "")

        mode_str = "direct" if self.direct_mode else f"proxy ({self.proxy_url})"
        print(
            f"[WINDSURF] Initialized: model='{self.model_name}', mode={mode_str}",
            file=sys.stderr,
            flush=True,
        )

    @property
    def _llm_type(self) -> str:
        return "windsurf-chat"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "WindsurfLLM":
        if isinstance(tools, list):
            self._tools = tools
        else:
            self._tools = [tools]
        return self

    # ─── Message Formatting ──────────────────────────────────────────────

    def _build_openai_payload(self, messages: list[BaseMessage], stream: bool = False) -> dict:
        """Build OpenAI-compatible payload for proxy mode."""
        formatted_messages = []
        system_content = "You are a helpful AI assistant."

        # Tool instructions
        tool_instructions = ""
        if self._tools:
            tools_desc_lines: list[str] = []
            for tool in self._tools:
                if isinstance(tool, dict):
                    name = tool.get("name", "tool")
                    description = tool.get("description", "")
                else:
                    name = getattr(tool, "name", getattr(tool, "__name__", "tool"))
                    description = getattr(tool, "description", "")
                if name:
                    tools_desc_lines.append(f"- {name}: {description}")
            tools_desc = "\n".join(tools_desc_lines)

            tool_instructions = (
                "CRITICAL: If you need to use tools, you MUST respond ONLY in the following JSON format. "
                "Any other text outside the JSON will cause a system error.\n\n"
                "AVAILABLE TOOLS:\n"
                f"{tools_desc}\n\n"
                "JSON FORMAT (ONLY IF USING TOOLS):\n"
                "{\n"
                '  "tool_calls": [\n'
                '    { "name": "tool_name", "args": { ... } }\n'
                "  ],\n"
                '  "final_answer": "Immediate feedback in UKRAINIAN (e.g., \'Зараз перевірю...\')."\n'
                "}\n\n"
                "If text response is enough (no tools needed), answer normally in Ukrainian.\n"
                "If you ALREADY checked results (ToolMessages provided), provide a final summary in plain text.\n"
            )

        for m in messages:
            role = "user"
            if isinstance(m, SystemMessage):
                role = "system"
                content = m.content if isinstance(m.content, str) else str(m.content)
                system_content = content + ("\n\n" + tool_instructions if tool_instructions else "")
                continue
            if isinstance(m, AIMessage):
                role = "assistant"
            elif isinstance(m, HumanMessage):
                role = "user"

            content = m.content
            # Windsurf free models don't support vision — strip images
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif item.get("type") == "image_url":
                            text_parts.append(
                                "[Image content not supported by Windsurf free models]"
                            )
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = " ".join(text_parts)

            formatted_messages.append({"role": role, "content": content})

        final_messages = [{"role": "system", "content": system_content}, *formatted_messages]

        return {
            "model": self.model_name,
            "messages": final_messages,
            "temperature": 0.1,
            "max_tokens": self.max_tokens,
            "stream": stream,
        }

    def _build_connect_rpc_payload(self, messages: list[BaseMessage]) -> dict:
        """Build Connect-RPC payload for direct Windsurf API mode."""
        chat_messages = []
        for m in messages:
            if isinstance(m, SystemMessage):
                role = ROLE_SYSTEM
            elif isinstance(m, AIMessage):
                role = ROLE_ASSISTANT
            else:
                role = ROLE_USER

            content = m.content
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = " ".join(text_parts)

            chat_messages.append({"role": role, "content": content})

        model_id = WINDSURF_FREE_MODELS.get(
            self.model_name or WINDSURF_DEFAULT_MODEL, self.model_name or WINDSURF_DEFAULT_MODEL
        )

        return {
            "chatMessages": chat_messages,
            "metadata": {
                "ideName": "windsurf",
                "ideVersion": "1.98.0",
                "extensionVersion": "1.42.0",
                "locale": "en",
                "sessionId": f"atlastrinity-{os.getpid()}",
                "requestId": "1",
                "installationId": self.installation_id,
            },
            "modelName": model_id,
        }

    # ─── Proxy Mode ──────────────────────────────────────────────────────

    def _call_proxy(self, payload: dict) -> dict:
        """Send OpenAI-compatible request to local proxy."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        response = requests.post(
            f"{self.proxy_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        return response.json()

    async def _call_proxy_async(self, payload: dict) -> dict:
        """Async OpenAI-compatible request to local proxy."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
            response = await client.post(
                f"{self.proxy_url}/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    # ─── Direct Mode (Connect-RPC) ───────────────────────────────────────

    def _call_direct(self, payload: dict) -> str:
        """Send Connect-RPC request directly to Windsurf API."""
        url = f"{self.api_server}/exa.api_server_pb.ApiServerService/GetChatMessage"
        headers = {
            "Content-Type": "application/connect+json",
            "Connect-Protocol-Version": "1",
            "Authorization": f"Basic {self.api_key}",
        }
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=300,
        )

        data = response.content
        if not data:
            raise RuntimeError("Empty response from Windsurf API")

        # Parse Connect-RPC framed response
        # Frame format: flag(1 byte) + length(4 bytes big-endian) + payload
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

            if flag == 0x02:  # Trailer/error frame
                error_info = frame_json.get("error", {})
                error_code = error_info.get("code", "unknown")
                error_msg = error_info.get("message", "Unknown error")
                raise RuntimeError(f"Windsurf API error ({error_code}): {error_msg}")

            # Data frame — extract content
            if "text" in frame_json:
                result_text += frame_json["text"]
            elif "content" in frame_json:
                result_text += frame_json["content"]
            elif "chatMessage" in frame_json:
                result_text += frame_json["chatMessage"].get("content", "")

        return result_text

    async def _call_direct_async(self, payload: dict) -> str:
        """Async Connect-RPC request to Windsurf API."""
        url = f"{self.api_server}/exa.api_server_pb.ApiServerService/GetChatMessage"
        headers = {
            "Content-Type": "application/connect+json",
            "Connect-Protocol-Version": "1",
            "Authorization": f"Basic {self.api_key}",
        }
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
            response = await client.post(url, headers=headers, json=payload)

        data = response.content
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

            if flag == 0x02:
                error_info = frame_json.get("error", {})
                raise RuntimeError(
                    f"Windsurf API error ({error_info.get('code', 'unknown')}): "
                    f"{error_info.get('message', 'Unknown error')}"
                )

            if "text" in frame_json:
                result_text += frame_json["text"]
            elif "content" in frame_json:
                result_text += frame_json["content"]
            elif "chatMessage" in frame_json:
                result_text += frame_json["chatMessage"].get("content", "")

        return result_text

    # ─── Result Processing ───────────────────────────────────────────────

    def _process_openai_result(self, data: dict, messages: list[BaseMessage]) -> ChatResult:
        """Process OpenAI-compatible response (from proxy)."""
        if not data.get("choices"):
            return ChatResult(
                generations=[
                    ChatGeneration(message=AIMessage(content="[WINDSURF] No response choice.")),
                ],
            )

        content = data["choices"][0]["message"]["content"]
        return self._process_content(content)

    def _process_content(self, content: str) -> ChatResult:
        """Process raw content string, extracting tool calls if needed."""
        if not self._tools:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

        tool_calls = []
        final_answer = ""
        try:
            json_start = content.find("{")
            json_end = content.rfind("}")
            if json_start >= 0 and json_end >= 0:
                parse_candidate = content[json_start : json_end + 1]
                parsed = json.loads(parse_candidate)
            else:
                parsed = json.loads(content)

            if isinstance(parsed, dict):
                calls = parsed.get("tool_calls") or []
                for idx, call in enumerate(calls):
                    tool_calls.append(
                        {
                            "id": f"call_{idx}",
                            "type": "tool_call",
                            "name": call.get("name"),
                            "args": call.get("args") or {},
                        },
                    )
                final_answer = str(parsed.get("final_answer", ""))
        except Exception:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

        if tool_calls:
            return ChatResult(
                generations=[
                    ChatGeneration(message=AIMessage(content=final_answer, tool_calls=tool_calls)),
                ],
            )
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=final_answer or content))],
        )

    # ─── LangChain Interface ─────────────────────────────────────────────

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Synchronous generation."""
        try:
            if self.direct_mode:
                payload = self._build_connect_rpc_payload(messages)
                content = self._call_direct(payload)
                return self._process_content(content)
            payload = self._build_openai_payload(messages)
            data = self._call_proxy(payload)
            return self._process_openai_result(data, messages)
        except Exception as e:
            print(f"[WINDSURF] Generation failed: {e}", file=sys.stderr, flush=True)
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content=f"[WINDSURF ERROR] {e}"))],
            )

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Asynchronous generation."""
        try:
            if self.direct_mode:
                payload = self._build_connect_rpc_payload(messages)
                content = await self._call_direct_async(payload)
                return self._process_content(content)
            payload = self._build_openai_payload(messages)
            data = await self._call_proxy_async(payload)
            return self._process_openai_result(data, messages)
        except Exception as e:
            print(f"[WINDSURF] Async generation failed: {e}", file=sys.stderr, flush=True)
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content=f"[WINDSURF ERROR] {e}"))],
            )

    def invoke_with_stream(
        self,
        messages: list[BaseMessage],
        *,
        on_delta: Callable[[str], None] | None = None,
    ) -> AIMessage:
        """Streaming invoke compatible with CopilotLLM interface."""
        try:
            if self.direct_mode:
                payload = self._build_connect_rpc_payload(messages)
                content = self._call_direct(payload)
            else:
                payload = self._build_openai_payload(messages, stream=True)
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                response = requests.post(
                    f"{self.proxy_url}/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=300,
                )
                response.raise_for_status()

                content = ""
                for line in response.iter_lines():
                    if not line:
                        continue
                    decoded = line.decode("utf-8")
                    if not decoded.startswith("data: "):
                        continue
                    data_str = decoded[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    if "choices" not in data or not data["choices"]:
                        continue
                    delta = data["choices"][0].get("delta", {})
                    piece = delta.get("content")
                    if not piece:
                        continue
                    content += piece
                    if on_delta:
                        try:
                            on_delta(piece)
                        except Exception:
                            pass

            # Parse tool calls if needed
            tool_calls = []
            if self._tools and content:
                try:
                    json_start = content.find("{")
                    json_end = content.rfind("}")
                    if json_start >= 0 and json_end >= 0:
                        parsed = json.loads(content[json_start : json_end + 1])
                        if isinstance(parsed, dict):
                            calls = parsed.get("tool_calls") or []
                            for idx, call in enumerate(calls):
                                name = call.get("name")
                                if not name:
                                    continue
                                tool_calls.append(
                                    {
                                        "id": f"call_{idx}",
                                        "type": "tool_call",
                                        "name": name,
                                        "args": call.get("args") or {},
                                    }
                                )
                            final_answer = str(parsed.get("final_answer", ""))
                            if tool_calls or final_answer:
                                content = final_answer or ""
                except Exception:
                    pass

            return AIMessage(content=content, tool_calls=tool_calls)

        except Exception as e:
            print(f"[WINDSURF] Stream error: {e}", file=sys.stderr, flush=True)
            return AIMessage(content=f"[WINDSURF ERROR] {e}")
