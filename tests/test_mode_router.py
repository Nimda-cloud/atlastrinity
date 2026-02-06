"""Tests for ModeRouter — LLM-first mode classification and profile building.

Tests cover:
- Profile building from LLM analysis results
- Mode normalization
- Fallback classification (emergency heuristic)
- Protocol and server merging (defaults + LLM overrides)
- ModeProfile properties and serialization
"""

import json
import os
import sys

import pytest

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestModeProfilesJSON:
    """Validate mode_profiles.json structure and completeness."""

    @pytest.fixture
    def profiles_data(self):
        path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "brain",
            "data",
            "mode_profiles.json",
        )
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_all_modes_present(self, profiles_data):
        expected_modes = {"chat", "deep_chat", "solo_task", "recall", "status", "task", "development"}
        actual_modes = {k for k in profiles_data if not k.startswith("_")}
        assert expected_modes == actual_modes, f"Missing modes: {expected_modes - actual_modes}"

    def test_each_mode_has_required_fields(self, profiles_data):
        required_fields = {
            "description",
            "llm_tier",
            "protocols",
            "servers",
            "tools_access",
            "prompt_template",
            "require_planning",
            "require_tools",
            "use_deep_persona",
        }
        for mode_name, mode_data in profiles_data.items():
            if mode_name.startswith("_"):
                continue
            missing = required_fields - set(mode_data.keys())
            assert not missing, f"Mode '{mode_name}' missing fields: {missing}"

    def test_protocol_registry_present(self, profiles_data):
        assert "_protocol_registry" in profiles_data
        registry = profiles_data["_protocol_registry"]
        assert "voice" in registry
        assert "search" in registry
        assert "task" in registry

    def test_deep_chat_has_deep_persona(self, profiles_data):
        assert profiles_data["deep_chat"]["use_deep_persona"] is True

    def test_chat_has_no_tools(self, profiles_data):
        assert profiles_data["chat"]["require_tools"] is False
        assert profiles_data["chat"]["tools_access"] == "none"

    def test_development_has_vibe(self, profiles_data):
        dev = profiles_data["development"]
        assert dev.get("use_vibe") is True
        assert "vibe" in dev["servers"]

    def test_task_requires_planning(self, profiles_data):
        assert profiles_data["task"]["require_planning"] is True
        assert profiles_data["task"]["trinity_required"] is True


class TestModeRouterBuildProfile:
    """Test ModeRouter.build_profile() — the core profile building logic."""

    @pytest.fixture
    def router(self):
        from src.brain.mode_router import ModeRouter

        return ModeRouter()

    def test_build_chat_profile(self, router):
        profile = router.build_profile({"intent": "chat", "voice_response": "Привіт!"})
        assert profile.mode == "chat"
        assert profile.intent == "chat"
        assert profile.use_deep_persona is False
        assert profile.require_tools is False
        assert "voice" in profile.all_protocols

    def test_build_deep_chat_profile(self, router):
        profile = router.build_profile({"intent": "deep_chat", "use_deep_persona": True})
        assert profile.mode == "deep_chat"
        assert profile.intent == "chat"  # backward compat: deep_chat → chat
        assert profile.use_deep_persona is True
        assert profile.llm_tier == "deep"

    def test_chat_upgraded_to_deep_chat_when_deep_persona(self, router):
        """If LLM says chat + use_deep_persona=True → auto-upgrade to deep_chat."""
        profile = router.build_profile({"intent": "chat", "use_deep_persona": True})
        assert profile.mode == "deep_chat"
        assert profile.use_deep_persona is True

    def test_build_solo_task_profile(self, router):
        profile = router.build_profile({"intent": "solo_task"})
        assert profile.mode == "solo_task"
        assert profile.require_tools is True
        assert profile.require_planning is False
        assert "search" in profile.all_protocols

    def test_build_task_profile(self, router):
        profile = router.build_profile({"intent": "task", "complexity": "high"})
        assert profile.mode == "task"
        assert profile.require_planning is True
        assert profile.trinity_required is True

    def test_build_development_profile(self, router):
        profile = router.build_profile({"intent": "development", "use_vibe": True})
        assert profile.mode == "development"
        assert profile.use_vibe is True
        assert profile.llm_tier == "deep"
        assert "vibe" in profile.all_servers

    def test_extra_servers_merged(self, router):
        profile = router.build_profile({
            "intent": "solo_task",
            "extra_servers": ["puppeteer", "github"],
        })
        assert "puppeteer" in profile.all_servers
        assert "github" in profile.all_servers
        # Default solo_task servers also present
        assert "duckduckgo-search" in profile.all_servers

    def test_extra_protocols_merged(self, router):
        profile = router.build_profile({
            "intent": "chat",
            "extra_protocols": ["maps", "data"],
        })
        assert "voice" in profile.all_protocols  # default
        assert "maps" in profile.all_protocols  # extra
        assert "data" in profile.all_protocols  # extra

    def test_no_duplicate_servers(self, router):
        profile = router.build_profile({
            "intent": "solo_task",
            "extra_servers": ["memory", "filesystem"],  # already in defaults
        })
        server_counts = {}
        for s in profile.all_servers:
            server_counts[s] = server_counts.get(s, 0) + 1
        duplicates = {s: c for s, c in server_counts.items() if c > 1}
        assert not duplicates, f"Duplicate servers: {duplicates}"

    def test_voice_response_preserved(self, router):
        profile = router.build_profile({
            "intent": "chat",
            "voice_response": "Вітаю, Олеже!",
        })
        assert profile.voice_response == "Вітаю, Олеже!"

    def test_to_dict_serialization(self, router):
        profile = router.build_profile({"intent": "task", "reason": "User wants automation"})
        d = profile.to_dict()
        assert d["mode"] == "task"
        assert d["intent"] == "task"
        assert isinstance(d["protocols"], list)
        assert isinstance(d["servers"], list)


class TestModeRouterNormalization:
    """Test mode name normalization."""

    @pytest.fixture
    def router(self):
        from src.brain.mode_router import ModeRouter

        return ModeRouter()

    def test_normalize_dev(self, router):
        profile = router.build_profile({"intent": "dev"})
        assert profile.mode == "development"

    def test_normalize_coding(self, router):
        profile = router.build_profile({"intent": "coding"})
        assert profile.mode == "development"

    def test_normalize_deepchat(self, router):
        profile = router.build_profile({"intent": "deepchat"})
        assert profile.mode == "deep_chat"

    def test_normalize_solotask(self, router):
        profile = router.build_profile({"intent": "solotask"})
        assert profile.mode == "solo_task"

    def test_unknown_mode_defaults_to_chat(self, router):
        profile = router.build_profile({"intent": "unknown_mode_xyz"})
        assert profile.mode == "chat"

    def test_unknown_mode_with_vibe_goes_to_development(self, router):
        profile = router.build_profile({"intent": "xyz", "use_vibe": True})
        assert profile.mode == "development"

    def test_unknown_mode_with_deep_persona_goes_to_deep_chat(self, router):
        profile = router.build_profile({"intent": "xyz", "use_deep_persona": True})
        assert profile.mode == "deep_chat"


class TestModeRouterFallback:
    """Test fallback_classify() — emergency heuristic."""

    @pytest.fixture
    def router(self):
        from src.brain.mode_router import ModeRouter

        return ModeRouter()

    def test_short_request_is_chat(self, router):
        profile = router.fallback_classify("Привіт!")
        assert profile.mode == "chat"

    def test_long_request_is_task(self, router):
        profile = router.fallback_classify(
            "Відкрий Finder, створи нову папку на робочому столі, перейменуй її на Проект "
            "і скопіюй туди всі файли з Downloads"
        )
        assert profile.mode == "task"

    def test_question_is_solo_task(self, router):
        profile = router.fallback_classify("Яка зараз погода у Львові?")
        assert profile.mode == "solo_task"

    def test_code_request_is_development(self, router):
        profile = router.fallback_classify("Виправ баг у модулі")
        assert profile.mode == "development"

    def test_action_verb_is_task(self, router):
        profile = router.fallback_classify("відкрий terminal")
        assert profile.mode == "task"

    def test_create_action_is_task(self, router):
        profile = router.fallback_classify("створи папку")
        assert profile.mode == "task"

    def test_medium_request_defaults_to_solo_task(self, router):
        profile = router.fallback_classify("Покажи мені останні новини")
        assert profile.mode == "solo_task"


class TestModeRouterStats:
    """Test statistics tracking."""

    def test_stats_after_classifications(self):
        from src.brain.mode_router import ModeRouter

        router = ModeRouter()
        router.build_profile({"intent": "chat"})
        router.build_profile({"intent": "task"})
        router.fallback_classify("test")

        stats = router.get_stats()
        assert stats["total_classifications"] == 3  # 2 build + 1 fallback (which calls build)
        assert stats["fallback_classifications"] == 1
        assert stats["profiles_loaded"] is True

    def test_available_modes(self):
        from src.brain.mode_router import ModeRouter

        router = ModeRouter()
        modes = router.get_available_modes()
        assert "chat" in modes
        assert "task" in modes
        assert "development" in modes
