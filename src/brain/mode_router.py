"""Mode Router — LLM-First Mode Classification & Profile Builder

Single entry point for determining execution mode from user request.
Replaces scattered keyword-based heuristics with LLM intelligence.

Architecture:
    1. LLM classifies user request → mode (chat/deep_chat/solo_task/task/development)
    2. ModeRouter builds ModeProfile from mode_profiles.json defaults
    3. LLM can override/extend defaults for edge cases
    4. Lightweight keyword fallback ONLY if LLM fails

Usage:
    from src.brain.mode_router import mode_router

    profile = await mode_router.classify(user_request, history, context)
    # profile.mode, profile.protocols, profile.servers, etc.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Any

from .logger import logger

# Load mode profiles at module level
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_PROFILES_PATH = os.path.join(_DATA_DIR, "mode_profiles.json")

_MODE_PROFILES: dict[str, Any] = {}
_PROTOCOL_REGISTRY: dict[str, str] = {}

def _load_profiles() -> None:
    """Load mode profiles from JSON."""
    global _MODE_PROFILES, _PROTOCOL_REGISTRY
    try:
        if os.path.exists(_PROFILES_PATH):
            with open(_PROFILES_PATH, encoding="utf-8") as f:
                data = json.load(f)
            _PROTOCOL_REGISTRY = data.pop("_protocol_registry", {})
            data.pop("_meta", None)
            _MODE_PROFILES = data
            logger.info(
                f"[MODE ROUTER] Loaded {len(_MODE_PROFILES)} mode profiles: {list(_MODE_PROFILES.keys())}"
            )
        else:
            logger.warning(f"[MODE ROUTER] Profiles not found at {_PROFILES_PATH}")
    except Exception as e:
        logger.error(f"[MODE ROUTER] Failed to load profiles: {e}")

_load_profiles()

@dataclass
class ModeProfile:
    """Complete execution profile for a classified request.

    Built from mode_profiles.json defaults + LLM overrides.
    Consumed by orchestrator, atlas.chat(), prompt builders.
    """

    mode: str
    reason: str = ""
    voice_response: str = ""
    enriched_request: str = ""
    complexity: str = "medium"

    # From mode_profiles.json defaults
    llm_tier: str = "standard"
    protocols: list[str] = field(default_factory=list)
    servers: list[str] = field(default_factory=list)
    tools_access: str = "none"
    prompt_template: str = "atlas_chat"
    require_planning: bool = False
    require_tools: bool = False
    use_deep_persona: bool = False
    use_sequential_thinking: bool = False
    use_vibe: bool = False
    trinity_required: bool = False

    # LLM-suggested overrides (can extend defaults)
    extra_servers: list[str] = field(default_factory=list)
    extra_protocols: list[str] = field(default_factory=list)

    @property
    def all_servers(self) -> list[str]:
        """Combined default + LLM-suggested servers."""
        seen = set()
        result = []
        for s in self.servers + self.extra_servers:
            if s not in seen:
                seen.add(s)
                result.append(s)
        return result

    @property
    def all_protocols(self) -> list[str]:
        """Combined default + LLM-suggested protocols."""
        seen = set()
        result = []
        for p in self.protocols + self.extra_protocols:
            if p not in seen:
                seen.add(p)
                result.append(p)
        return result

    @property
    def intent(self) -> str:
        """Backward-compatible alias: maps mode to legacy intent names."""
        # deep_chat → chat (for orchestrator routing)
        if self.mode == "deep_chat":
            return "chat"
        return self.mode

    def to_dict(self) -> dict[str, Any]:
        """Serialize for logging/passing to prompts."""
        return {
            "mode": self.mode,
            "intent": self.intent,
            "reason": self.reason,
            "voice_response": self.voice_response,
            "enriched_request": self.enriched_request,
            "complexity": self.complexity,
            "llm_tier": self.llm_tier,
            "protocols": self.all_protocols,
            "servers": self.all_servers,
            "tools_access": self.tools_access,
            "prompt_template": self.prompt_template,
            "require_planning": self.require_planning,
            "require_tools": self.require_tools,
            "use_deep_persona": self.use_deep_persona,
            "use_sequential_thinking": self.use_sequential_thinking,
            "use_vibe": self.use_vibe,
            "trinity_required": self.trinity_required,
        }

class ModeRouter:
    """LLM-first mode classification with declarative profile building.

    Flow:
        1. classify() receives LLM analysis result (from atlas.analyze_request)
        2. Extracts mode from LLM response
        3. Builds ModeProfile by merging mode_profiles.json defaults with LLM overrides
        4. Falls back to lightweight heuristic ONLY if LLM returned no mode
    """

    def __init__(self) -> None:
        self._classification_count = 0
        self._fallback_count = 0

    def build_profile(self, llm_analysis: dict[str, Any]) -> ModeProfile:
        """Build a ModeProfile from LLM analysis result.

        Args:
            llm_analysis: Result from atlas.analyze_request() containing:
                - intent/mode: classified mode name
                - reason, voice_response, enriched_request, complexity
                - use_deep_persona, use_vibe
                - Optional: extra_servers, extra_protocols

        Returns:
            Complete ModeProfile ready for consumption by orchestrator/prompts.
        """
        self._classification_count += 1

        # Extract mode from LLM result (supports both 'mode' and legacy 'intent')
        raw_mode = llm_analysis.get("mode") or llm_analysis.get("intent", "chat")

        # Normalize mode name
        mode = self._normalize_mode(raw_mode, llm_analysis)

        # Get defaults from profile
        defaults = _MODE_PROFILES.get(mode, _MODE_PROFILES.get("chat", {}))

        # Build profile: defaults + LLM overrides
        profile = ModeProfile(
            mode=mode,
            reason=llm_analysis.get("reason", ""),
            voice_response=llm_analysis.get("voice_response", ""),
            enriched_request=llm_analysis.get("enriched_request", ""),
            complexity=str(llm_analysis.get("complexity", defaults.get("complexity", "medium"))),
            llm_tier=defaults.get("llm_tier", "standard"),
            protocols=list(defaults.get("protocols", [])),
            servers=list(defaults.get("servers", [])),
            tools_access=defaults.get("tools_access", "none"),
            prompt_template=defaults.get("prompt_template", "atlas_chat"),
            require_planning=defaults.get("require_planning", False),
            require_tools=defaults.get("require_tools", False),
            use_deep_persona=bool(
                llm_analysis.get("use_deep_persona", defaults.get("use_deep_persona", False))
            ),
            use_sequential_thinking=defaults.get("use_sequential_thinking", False),
            use_vibe=bool(llm_analysis.get("use_vibe", defaults.get("use_vibe", False))),
            trinity_required=defaults.get("trinity_required", False),
            extra_servers=llm_analysis.get("extra_servers", []),
            extra_protocols=llm_analysis.get("extra_protocols", []),
        )

        # If LLM says deep persona but mode is chat → upgrade to deep_chat
        if profile.use_deep_persona and profile.mode == "chat":
            deep_defaults = _MODE_PROFILES.get("deep_chat", {})
            profile.mode = "deep_chat"
            profile.llm_tier = deep_defaults.get("llm_tier", "deep")
            # Merge deep_chat servers
            for s in deep_defaults.get("servers", []):
                if s not in profile.servers:
                    profile.servers.append(s)

        logger.info(
            f"[MODE ROUTER] Profile built: mode={profile.mode}, "
            f"protocols={profile.all_protocols}, "
            f"servers_count={len(profile.all_servers)}, "
            f"deep_persona={profile.use_deep_persona}"
        )

        return profile

    def _normalize_mode(self, raw_mode: str, llm_analysis: dict[str, Any]) -> str:
        """Normalize LLM's mode output to a valid mode name."""
        mode_lower = raw_mode.lower().strip()

        # Direct mappings
        mode_map = {
            "chat": "chat",
            "deep_chat": "deep_chat",
            "deepchat": "deep_chat",
            "solo_task": "solo_task",
            "solotask": "solo_task",
            "solo": "solo_task",
            "task": "task",
            "development": "development",
            "dev": "development",
            "coding": "development",
            "recall": "recall",
            "status": "status",
        }

        normalized = mode_map.get(mode_lower)
        if normalized:
            return normalized

        # If mode unknown, check if LLM set use_deep_persona
        if llm_analysis.get("use_deep_persona"):
            return "deep_chat"

        # If mode unknown, check if LLM set use_vibe
        if llm_analysis.get("use_vibe"):
            return "development"

        # Default fallback
        logger.warning(f"[MODE ROUTER] Unknown mode '{raw_mode}', defaulting to 'chat'")
        self._fallback_count += 1
        return "chat"

    def fallback_classify(self, user_request: str) -> ModeProfile:
        """Emergency fallback: lightweight heuristic classification.

        ONLY used when LLM classification completely fails.
        Deliberately simple — 7 rules, no keyword explosion.
        """
        self._fallback_count += 1
        request_lower = user_request.lower().strip()
        word_count = len(user_request.split())

        # Rule 1: Code-related words → development (check BEFORE word count)
        code_indicators = ["код", "code", "баг", "bug", "рефактор", "refactor", "програм", "app"]
        if any(w in request_lower for w in code_indicators):
            return self.build_profile({"mode": "development"})

        # Rule 2: Action verbs → task (check BEFORE word count, catches "відкрий X")
        action_verbs = [
            "відкрий",
            "зроби",
            "створи",
            "встанови",
            "запусти",
            "видали",
            "скопіюй",
            "перемісти",
            "надішли",
            "побудуй",
            "налаштуй",
            "open",
            "create",
            "install",
            "run",
            "delete",
            "move",
            "send",
            "build",
        ]
        if any(request_lower.startswith(v) or f" {v}" in request_lower for v in action_verbs):
            return self.build_profile({"mode": "task"})

        # Rule 3: Very short + no action verbs → chat
        if word_count <= 3:
            return self.build_profile({"mode": "chat"})

        # Rule 4: Long complex request → task
        if word_count >= 15:
            return self.build_profile({"mode": "task", "complexity": "high"})

        # Rule 5: Question mark + medium length → solo_task
        if "?" in user_request and word_count < 10:
            return self.build_profile({"mode": "solo_task"})

        # Rule 6: Default → solo_task (safer than chat — allows tool use)
        return self.build_profile({"mode": "solo_task"})

    def get_protocol_registry(self) -> dict[str, str]:
        """Returns protocol name → filename mapping."""
        return dict(_PROTOCOL_REGISTRY)

    def get_available_modes(self) -> list[str]:
        """Returns list of all available mode names."""
        return list(_MODE_PROFILES.keys())

    def get_mode_defaults(self, mode: str) -> dict[str, Any]:
        """Returns raw defaults for a mode from profiles."""
        return dict(_MODE_PROFILES.get(mode, {}))

    def get_stats(self) -> dict[str, Any]:
        """Usage statistics."""
        return {
            "total_classifications": self._classification_count,
            "fallback_classifications": self._fallback_count,
            "fallback_rate_pct": (
                round(self._fallback_count / self._classification_count * 100, 2)
                if self._classification_count > 0
                else 0
            ),
            "available_modes": self.get_available_modes(),
            "profiles_loaded": bool(_MODE_PROFILES),
        }

    def reload_profiles(self) -> None:
        """Hot-reload mode profiles."""
        _load_profiles()
        logger.info("[MODE ROUTER] Profiles reloaded")

# Global singleton
mode_router = ModeRouter()
