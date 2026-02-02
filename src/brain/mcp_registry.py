"""MCP Registry - Unified Tool Descriptions and Schemas

Single source of truth for all MCP server definitions, tool schemas,
and documentation. Used by all agents (Atlas, Tetyana, Grisha).

Note: This file loads definitions from JSON files in src/brain/data/
to prevent language server (Pyrefly) stack overflow crashes.
"""

import json
import os
from typing import Any

# Paths to data files
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(CURRENT_DIR, "data")
CATALOG_PATH = os.path.join(DATA_DIR, "mcp_catalog.json")
SCHEMAS_PATH = os.path.join(DATA_DIR, "tool_schemas.json")
# Protocol paths (moved to protocols/ subdirectory)
PROTOCOLS_DIR = os.path.join(DATA_DIR, "protocols")
VIBE_DOCS_PATH = os.path.join(PROTOCOLS_DIR, "vibe_docs.txt")
VOICE_PROTOCOL_PATH = os.path.join(PROTOCOLS_DIR, "voice_protocol.txt")
SEARCH_PROTOCOL_PATH = os.path.join(PROTOCOLS_DIR, "search_protocol.txt")
STORAGE_PROTOCOL_PATH = os.path.join(PROTOCOLS_DIR, "storage_protocol.txt")
SDLC_PROTOCOL_PATH = os.path.join(PROTOCOLS_DIR, "sdlc_protocol.txt")
TASK_PROTOCOL_PATH = os.path.join(PROTOCOLS_DIR, "task_protocol.txt")
DATA_PROTOCOL_PATH = os.path.join(PROTOCOLS_DIR, "data_protocol.txt")
SYSTEM_MASTERY_PROTOCOL_PATH = os.path.join(PROTOCOLS_DIR, "system_mastery_protocol.txt")
HACKING_PROTOCOL_PATH = os.path.join(PROTOCOLS_DIR, "hacking_sysadmin_protocol.md")
MAPS_PROTOCOL_PATH = os.path.join(PROTOCOLS_DIR, "maps_protocol.md")

# Global variables to store loaded data
SERVER_CATALOG: dict[str, dict[str, Any]] = {}
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {}
VIBE_DOCUMENTATION: str = ""
VOICE_PROTOCOL: str = ""
SEARCH_PROTOCOL: str = ""
STORAGE_PROTOCOL: str = ""
SDLC_PROTOCOL: str = ""
TASK_PROTOCOL: str = ""
DATA_PROTOCOL: str = ""
SYSTEM_MASTERY_PROTOCOL: str = ""
HACKING_PROTOCOL: str = ""
MAPS_PROTOCOL: str = ""

# Cache for frequently accessed data
_tool_lookup_cache: dict[str, str | None] = {}  # tool_name -> server_name
_schema_cache_hits: int = 0
_schema_cache_misses: int = 0


def load_registry():
    """Load registry data from JSON and text files."""
    global \
        SERVER_CATALOG, \
        TOOL_SCHEMAS, \
        VIBE_DOCUMENTATION, \
        VOICE_PROTOCOL, \
        SEARCH_PROTOCOL, \
        STORAGE_PROTOCOL, \
        SDLC_PROTOCOL, \
        TASK_PROTOCOL, \
        DATA_PROTOCOL, \
        SYSTEM_MASTERY_PROTOCOL, \
        HACKING_PROTOCOL, \
        MAPS_PROTOCOL

    try:
        # Load Catalog
        if os.path.exists(CATALOG_PATH):
            with open(CATALOG_PATH, encoding="utf-8") as f:
                SERVER_CATALOG = json.load(f)
        else:
            print(f"[Here be Dragons] Warning: Catalog file not found at {CATALOG_PATH}")

        # Load Schemas
        if os.path.exists(SCHEMAS_PATH):
            with open(SCHEMAS_PATH, encoding="utf-8") as f:
                TOOL_SCHEMAS = json.load(f)
        else:
            print(f"[Here be Dragons] Warning: Schemas file not found at {SCHEMAS_PATH}")

        # Load Vibe Docs
        if os.path.exists(VIBE_DOCS_PATH):
            with open(VIBE_DOCS_PATH, encoding="utf-8") as f:
                VIBE_DOCUMENTATION = f.read()
        else:
            VIBE_DOCUMENTATION = "Vibe documentation not found."

        # Load Voice Protocol
        if os.path.exists(VOICE_PROTOCOL_PATH):
            with open(VOICE_PROTOCOL_PATH, encoding="utf-8") as f:
                VOICE_PROTOCOL = f.read()
        else:
            VOICE_PROTOCOL = "Voice protocol not found."
        # Load Search Protocol
        if os.path.exists(SEARCH_PROTOCOL_PATH):
            with open(SEARCH_PROTOCOL_PATH, encoding="utf-8") as f:
                SEARCH_PROTOCOL = f.read()
        else:
            SEARCH_PROTOCOL = "Search protocol not found."

        # Load Storage Protocol
        if os.path.exists(STORAGE_PROTOCOL_PATH):
            with open(STORAGE_PROTOCOL_PATH, encoding="utf-8") as f:
                STORAGE_PROTOCOL = f.read()
        else:
            STORAGE_PROTOCOL = "Storage protocol not found."
        # Load SDLC Protocol
        if os.path.exists(SDLC_PROTOCOL_PATH):
            with open(SDLC_PROTOCOL_PATH, encoding="utf-8") as f:
                SDLC_PROTOCOL = f.read()
        else:
            SDLC_PROTOCOL = "SDLC protocol not found."

        # Load Task Protocol
        if os.path.exists(TASK_PROTOCOL_PATH):
            with open(TASK_PROTOCOL_PATH, encoding="utf-8") as f:
                TASK_PROTOCOL = f.read()
        else:
            TASK_PROTOCOL = "Task protocol not found."

        # Load Data Protocol
        if os.path.exists(DATA_PROTOCOL_PATH):
            with open(DATA_PROTOCOL_PATH, encoding="utf-8") as f:
                DATA_PROTOCOL = f.read()
        else:
            DATA_PROTOCOL = "Data protocol not found."

        # Load System Mastery Protocol
        if os.path.exists(SYSTEM_MASTERY_PROTOCOL_PATH):
            with open(SYSTEM_MASTERY_PROTOCOL_PATH, encoding="utf-8") as f:
                SYSTEM_MASTERY_PROTOCOL = f.read()
        else:
            SYSTEM_MASTERY_PROTOCOL = "System mastery protocol not found."

        # Load Hacking Protocol
        if os.path.exists(HACKING_PROTOCOL_PATH):
            with open(HACKING_PROTOCOL_PATH, encoding="utf-8") as f:
                HACKING_PROTOCOL = f.read()
        else:
            HACKING_PROTOCOL = "Hacking & Sysadmin protocol not found."

        # Load Maps Protocol
        if os.path.exists(MAPS_PROTOCOL_PATH):
            with open(MAPS_PROTOCOL_PATH, encoding="utf-8") as f:
                MAPS_PROTOCOL = f.read()
        else:
            MAPS_PROTOCOL = "Maps protocol not found."

    except Exception as e:
        print(f"[Here be Dragons] Error loading MCP registry: {e}")


# Load data immediately on import
load_registry()


# ═══════════════════════════════════════════════════════════════════════════════
#                           UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════


def get_server_catalog_for_prompt(include_key_tools: bool = True) -> str:
    """Generate LLM-readable server catalog for prompts.
    This replaces the hardcoded DEFAULT_REALM_CATALOG in common.py.
    """
    lines = ["AVAILABLE REALMS (MCP Servers):", ""]

    # Group by tier
    by_tier: dict[int, list[dict]] = {}
    for name, info in SERVER_CATALOG.items():
        tier = info.get("tier", 4)
        if tier not in by_tier:
            by_tier[tier] = []
        by_tier[tier].append(info)

    tier_names = {
        1: "TIER 1 - CORE",
        2: "TIER 2 - HIGH PRIORITY",
        3: "TIER 3 - OPTIONAL",
        4: "TIER 4 - SPECIALIZED",
    }

    for tier in sorted(by_tier.keys()):
        lines.append(f"{tier_names.get(tier, f'TIER {tier}')}:")

        for server in by_tier[tier]:
            name = server["name"]
            desc = server["description"]
            lines.append(f"- {name}: {desc}")

            if include_key_tools and "key_tools" in server:
                tools = ", ".join(server["key_tools"][:5])
                if len(server["key_tools"]) > 5:
                    tools += ", ..."
                lines.append(f"  Key tools: {tools}")

            if "priority_note" in server:
                lines.append(f"  NOTE: {server['priority_note']}")

        lines.append("")

    lines.append("DEPRECATED (Use macos-use instead):")
    lines.append("- fetch → macos-use_fetch_url")
    lines.append("- time → macos-use_get_time")
    lines.append("- apple-mcp → macos-use Calendar/Reminders/Notes/Mail tools")
    lines.append("- git → macos-use execute_command('git ...')")
    lines.append("- notes → filesystem or macos-use (Apple Notes)")
    lines.append("- search → macos-use chrome or fetch_url")
    lines.append("- docker, postgres, slack → Disabled/Removed")
    lines.append("")
    lines.append(
        "CRITICAL: Do NOT invent high-level tools. Use only the real TOOLS found inside these Realms.",
    )

    return "\n".join(lines)


def get_tool_schema(tool_name: str) -> dict[str, Any] | None:
    """Get schema for a specific tool.
    Resolves aliases to their canonical form.
    Uses caching for performance.
    """
    global _schema_cache_hits, _schema_cache_misses

    schema = TOOL_SCHEMAS.get(tool_name)
    if schema:
        _schema_cache_hits += 1
        if "alias_for" in schema:
            canonical = TOOL_SCHEMAS.get(schema["alias_for"])
            return canonical
        return schema

    _schema_cache_misses += 1
    return None


def get_server_for_tool(tool_name: str) -> str | None:
    """Get the server name for a tool.
    Uses cache for performance.
    """
    # Check cache first
    if tool_name in _tool_lookup_cache:
        return _tool_lookup_cache[tool_name]

    # Cache miss - look up in schemas
    schema = TOOL_SCHEMAS.get(tool_name)
    result = None
    if schema:
        if "alias_for" in schema:
            result = schema.get("server")
        else:
            result = schema.get("server")

    # Cache the result (even if None)
    _tool_lookup_cache[tool_name] = result
    return result


def get_servers_for_task(task_type: str) -> list[str]:
    """Suggest servers based on task type.
    Now delegates to BehaviorEngine for config-driven classification.
    """
    from src.brain.behavior_engine import behavior_engine

    # Delegate to behavior engine (replaces 80+ lines of hardcoded conditionals)
    servers = behavior_engine.classify_task(task_type)

    if servers:
        return servers

    # Default fallback
    return ["macos-use", "filesystem"]


def get_all_tool_names() -> list[str]:
    """Get list of all available tool names (excluding aliases)."""
    return [name for name, schema in TOOL_SCHEMAS.items() if "alias_for" not in schema]


def get_tool_names_for_server(server_name: str) -> list[str]:
    """Get all tool names for a specific server."""
    return [
        name
        for name, schema in TOOL_SCHEMAS.items()
        if schema.get("server") == server_name and "alias_for" not in schema
    ]


def get_registry_stats() -> dict[str, Any]:
    """Get statistics about registry usage and cache performance."""
    total_requests = _schema_cache_hits + _schema_cache_misses
    cache_hit_rate = (_schema_cache_hits / total_requests * 100) if total_requests > 0 else 0

    return {
        "total_servers": len(SERVER_CATALOG),
        "total_tools": len(TOOL_SCHEMAS),
        "cache_size": len(_tool_lookup_cache),
        "cache_hits": _schema_cache_hits,
        "cache_misses": _schema_cache_misses,
        "cache_hit_rate_pct": round(cache_hit_rate, 2),
        "schemas_loaded": bool(TOOL_SCHEMAS),
        "catalog_loaded": bool(SERVER_CATALOG),
    }


def clear_caches() -> None:
    """Clear all internal caches. Useful for testing or after registry reload."""
    global _schema_cache_hits, _schema_cache_misses  # noqa: PLW0603

    _tool_lookup_cache.clear()
    _schema_cache_hits = 0
    _schema_cache_misses = 0


def validate_tool_call(tool_name: str, arguments: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate if a tool call has all required arguments.

    Returns:
        (is_valid, error_message)
    """
    schema = get_tool_schema(tool_name)
    if not schema:
        return True, None  # No schema = cannot validate, pass through

    required = schema.get("required", [])
    missing = [arg for arg in required if arg not in arguments]

    if missing:
        return False, f"Missing required arguments: {', '.join(missing)}"

    return True, None
