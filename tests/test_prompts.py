from brain.prompts import AgentPrompts


def test_agent_prompts_exports():
    assert hasattr(AgentPrompts, "ATLAS")
    assert hasattr(AgentPrompts, "TETYANA")
    assert hasattr(AgentPrompts, "GRISHA")


def test_grisha_prompt_contains_dynamic_catalog():
    """Verify Grisha's prompt includes dynamic server catalog from mcp_registry."""
    grisha = AgentPrompts.GRISHA
    assert isinstance(grisha, dict)
    sys_prompt = grisha.get("SYSTEM_PROMPT", "")

    # Check that catalog is properly interpolated from mcp_registry
    assert "TIER 1 - CORE" in sys_prompt or "macos-use" in sys_prompt

    # Check MCP verification tools are mentioned
    assert "macos-use_refresh_traversal" in sys_prompt or "execute_command" in sys_prompt


def test_atlas_prompt_contains_dynamic_catalog():
    """Verify Atlas's prompt includes dynamic server catalog from mcp_registry."""
    atlas = AgentPrompts.ATLAS
    assert isinstance(atlas, dict)
    sys_prompt = atlas.get("SYSTEM_PROMPT", "")

    # Check that catalog is properly interpolated
    assert "TIER 1 - CORE" in sys_prompt or "macos-use" in sys_prompt


def test_tetyana_prompt_contains_dynamic_catalog():
    """Verify Tetyana's prompt includes dynamic server catalog from mcp_registry."""
    tetyana = AgentPrompts.TETYANA
    assert isinstance(tetyana, dict)
    sys_prompt = tetyana.get("SYSTEM_PROMPT", "")

    # Check that catalog is properly interpolated
    assert "TIER 1 - CORE" in sys_prompt or "macos-use" in sys_prompt


def test_prompts_no_uninterpolated_placeholders():
    """Verify no literal placeholders remain in prompts."""
    for name in ["ATLAS", "TETYANA", "GRISHA"]:
        prompt = getattr(AgentPrompts, name).get("SYSTEM_PROMPT", "")
        assert "{DEFAULT_REALM_CATALOG}" not in prompt, f"{name} has uninterpolated catalog"
        assert "{VIBE_TOOLS_DOCUMENTATION}" not in prompt, f"{name} has uninterpolated vibe docs"
        assert "{VOICE_PROTOCOL}" not in prompt, f"{name} has uninterpolated voice protocol"
