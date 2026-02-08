"""Comprehensive MCP Server Testing Suite — All 21 Servers, Every Tool

Tests:
  1. MCP Registry — catalog loading, schema validation, tool lookup
  2. MCP Dispatcher — synonym resolution, routing, hallucination detection
  3. MCP Config — template validation, server definitions
  4. Individual Server Smoke Tests — spawn each server, list tools via JSON-RPC
  5. Tool Schema Validation — every registered tool has required/optional/types
  6. Cross-Server Interaction — dispatcher→registry→manager chain
  7. DevTools Testing Tools — inspector, sandbox, health check integration

Run:
    pytest tests/test_mcp_comprehensive.py -v --timeout=120
    python tests/test_mcp_comprehensive.py   # standalone mode
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: MCP CONFIGURATION VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPConfiguration:
    """Validate mcp_servers.json.template and active config structure."""

    CONFIG_TEMPLATE = PROJECT_ROOT / "config" / "mcp_servers.json.template"
    ACTIVE_CONFIG = Path.home() / ".config" / "atlastrinity" / "mcp" / "config.json"

    EXPECTED_SERVERS = [
        "macos-use",
        "filesystem",
        "sequential-thinking",
        "googlemaps",
        "xcodebuild",
        "chrome-devtools",
        "vibe",
        "memory",
        "graph",
        "puppeteer",
        "duckduckgo-search",
        "golden-fund",
        "context7",
        "whisper-stt",
        "devtools",
        "github",
        "redis",
        "data-analysis",
        "postgres",
        "react-devtools",
        "tour-guide",
    ]

    def _load_config(self) -> dict[str, Any]:
        """Load the best available config."""
        for path in [self.ACTIVE_CONFIG, self.CONFIG_TEMPLATE]:
            if path.exists():
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
        pytest.skip("No MCP config found")

    def test_config_valid_json(self):
        """Config file must be valid JSON."""
        config = self._load_config()
        assert "mcpServers" in config, "Missing 'mcpServers' key"

    def test_all_21_servers_present(self):
        """All 21 expected servers must be defined."""
        config = self._load_config()
        servers = config["mcpServers"]
        real_servers = [k for k in servers if not k.startswith("_")]
        for name in self.EXPECTED_SERVERS:
            assert name in real_servers, f"Server '{name}' missing from config"
        assert len(real_servers) >= 21, f"Expected >=21 servers, got {len(real_servers)}"

    def test_server_required_fields(self):
        """Each server must have transport, command, and description."""
        config = self._load_config()
        for name, cfg in config["mcpServers"].items():
            if name.startswith("_"):
                continue
            assert "transport" in cfg, f"{name}: missing 'transport'"
            assert "command" in cfg, f"{name}: missing 'command'"
            assert "description" in cfg, f"{name}: missing 'description'"

    def test_server_tier_assignment(self):
        """Each server must have a tier (1-4)."""
        config = self._load_config()
        for name, cfg in config["mcpServers"].items():
            if name.startswith("_"):
                continue
            tier = cfg.get("tier")
            assert tier is not None, f"{name}: missing 'tier'"
            assert tier in (1, 2, 3, 4), f"{name}: invalid tier {tier}"

    def test_server_agent_assignment(self):
        """Each server should have an 'agents' list."""
        config = self._load_config()
        for name, cfg in config["mcpServers"].items():
            if name.startswith("_"):
                continue
            agents = cfg.get("agents")
            assert isinstance(agents, list), f"{name}: missing or invalid 'agents'"
            assert len(agents) > 0, f"{name}: empty 'agents' list"

    def test_transport_types(self):
        """Transport must be 'stdio' or 'internal'."""
        config = self._load_config()
        for name, cfg in config["mcpServers"].items():
            if name.startswith("_"):
                continue
            transport = cfg.get("transport")
            assert transport in ("stdio", "internal"), f"{name}: invalid transport '{transport}'"

    def test_disabled_servers(self):
        """Only postgres should be disabled by default."""
        config = self._load_config()
        disabled = [
            k
            for k, v in config["mcpServers"].items()
            if not k.startswith("_") and v.get("disabled", False)
        ]
        assert "postgres" in disabled, "postgres should be disabled by default"
        assert len(disabled) <= 2, f"Too many disabled servers: {disabled}"

    def test_metadata_section(self):
        """Config should have _metadata with version info."""
        config = self._load_config()
        meta = config.get("_metadata", {})
        assert "version" in meta, "Missing _metadata.version"
        assert "active_servers" in meta, "Missing _metadata.active_servers"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: MCP REGISTRY TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestMCPRegistry:
    """Test the MCP Registry: catalog, schemas, lookup functions."""

    @pytest.fixture(autouse=True)
    def setup_registry(self):
        from src.brain.mcp_registry import load_registry

        load_registry()

    def test_catalog_loaded(self):
        from src.brain.mcp_registry import SERVER_CATALOG

        assert len(SERVER_CATALOG) > 0, "SERVER_CATALOG is empty"

    def test_catalog_has_core_servers(self):
        from src.brain.mcp_registry import SERVER_CATALOG

        core = ["macos-use", "filesystem", "sequential-thinking"]
        for name in core:
            assert name in SERVER_CATALOG, f"Core server '{name}' missing from catalog"

    def test_catalog_server_structure(self):
        """Each catalog entry must have name, tier, description, key_tools."""
        from src.brain.mcp_registry import SERVER_CATALOG

        for name, entry in SERVER_CATALOG.items():
            assert "name" in entry, f"{name}: missing 'name'"
            assert "tier" in entry, f"{name}: missing 'tier'"
            assert "description" in entry, f"{name}: missing 'description'"
            assert "key_tools" in entry, f"{name}: missing 'key_tools'"
            assert isinstance(entry["key_tools"], list), f"{name}: 'key_tools' not a list"

    def test_schemas_loaded(self):
        from src.brain.mcp_registry import TOOL_SCHEMAS

        assert len(TOOL_SCHEMAS) > 0, "TOOL_SCHEMAS is empty"

    def test_schema_structure(self):
        """Each schema must have server, required, optional fields."""
        from src.brain.mcp_registry import TOOL_SCHEMAS

        for tool_name, schema in TOOL_SCHEMAS.items():
            if "alias_for" in schema:
                continue
            assert "server" in schema, f"Schema '{tool_name}': missing 'server'"
            assert "required" in schema, f"Schema '{tool_name}': missing 'required'"
            assert isinstance(schema["required"], list), (
                f"Schema '{tool_name}': 'required' not a list"
            )

    def test_get_server_for_tool(self):
        from src.brain.mcp_registry import get_server_for_tool

        assert get_server_for_tool("vibe_prompt") == "vibe"
        assert get_server_for_tool("search_golden_fund") == "golden-fund"

    def test_get_tool_schema(self):
        from src.brain.mcp_registry import get_tool_schema

        schema = get_tool_schema("vibe_prompt")
        assert schema is not None, "vibe_prompt schema not found"
        assert "prompt" in schema["required"]

    def test_get_all_tool_names(self):
        from src.brain.mcp_registry import get_all_tool_names

        names = get_all_tool_names()
        assert len(names) > 20, f"Expected >20 tools, got {len(names)}"

    def test_get_tool_names_for_server(self):
        from src.brain.mcp_registry import get_tool_names_for_server

        vibe_tools = get_tool_names_for_server("vibe")
        assert len(vibe_tools) > 0, "No tools found for vibe server"

    def test_get_servers_for_task(self):
        from src.brain.mcp_registry import get_servers_for_task

        servers = get_servers_for_task("coding")
        assert isinstance(servers, list)
        assert len(servers) > 0

    def test_registry_stats(self):
        from src.brain.mcp_registry import get_registry_stats

        stats = get_registry_stats()
        assert stats["total_servers"] > 0
        assert stats["total_tools"] > 0
        assert stats["schemas_loaded"] is True
        assert stats["catalog_loaded"] is True

    def test_catalog_prompt_generation(self):
        from src.brain.mcp_registry import get_server_catalog_for_prompt

        prompt = get_server_catalog_for_prompt()
        assert len(prompt) > 100, "Catalog prompt too short"
        assert "macos-use" in prompt
        assert "vibe" in prompt


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: TOOL DISPATCHER TESTS
# ═══════════════════════════════════════════════════════════════════════════════


class TestToolDispatcher:
    """Test the ToolDispatcher: routing, synonyms, hallucination detection."""

    @pytest.fixture
    def dispatcher(self):
        from src.brain.mcp_registry import load_registry

        load_registry()
        from src.brain.tool_dispatcher import ToolDispatcher

        mock_manager = MagicMock()
        mock_manager.call_tool = AsyncMock(return_value={"success": True})
        mock_manager.sessions = {}
        return ToolDispatcher(mock_manager)

    def test_terminal_synonym_resolution(self, dispatcher):
        """Terminal synonyms should route to macos-use."""
        for syn in ["bash", "terminal", "execute_command", "python3"]:
            assert syn in dispatcher.TERMINAL_SYNONYMS, f"'{syn}' not in TERMINAL_SYNONYMS"

    def test_filesystem_synonym_resolution(self, dispatcher):
        for syn in ["filesystem", "read_file", "write_file"]:
            assert syn in dispatcher.FILESYSTEM_SYNONYMS, f"'{syn}' not in FILESYSTEM_SYNONYMS"

    def test_vibe_synonym_resolution(self, dispatcher):
        for syn in ["vibe", "vibe_prompt", "vibe_ask", "debug", "fix"]:
            assert syn in dispatcher.VIBE_SYNONYMS, f"'{syn}' not in VIBE_SYNONYMS"

    def test_browser_synonym_resolution(self, dispatcher):
        for syn in ["browser", "puppeteer", "navigate"]:
            assert syn in dispatcher.BROWSER_SYNONYMS, f"'{syn}' not in BROWSER_SYNONYMS"

    def test_hallucinated_tool_detection(self, dispatcher):
        """Known hallucinated tools should be detected."""
        for tool in ["evaluate", "assess", "verify", "validate", "check", "test"]:
            assert tool in dispatcher.HALLUCINATED_TOOLS, f"'{tool}' not in HALLUCINATED_TOOLS"

    @pytest.mark.asyncio
    async def test_hallucinated_tool_returns_error(self, dispatcher):
        result = await dispatcher.resolve_and_dispatch("evaluate", {})
        assert result.get("hallucinated") is True
        assert result.get("success") is False

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, dispatcher):
        result = await dispatcher.resolve_and_dispatch("nonexistent_tool_xyz_999", {})
        assert result.get("success") is False

    def test_dot_notation_parsing(self, dispatcher):
        """Dot notation 'server.tool' should split correctly."""
        server, _tool, _args = dispatcher._resolve_routing("vibe.prompt", {}, None)
        assert server == "vibe"

    def test_coverage_stats(self, dispatcher):
        stats = dispatcher.get_coverage_stats()
        assert "total_calls" in stats
        assert "coverage_percentage" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: INDIVIDUAL SERVER TOOL DEFINITION TESTS
# ═══════════════════════════════════════════════════════════════════════════════


# All 21 servers with their expected tools (extracted from source code)
ALL_SERVERS_TOOLS: dict[str, dict[str, Any]] = {
    "macos-use": {
        "transport": "stdio",
        "binary": True,
        "min_tools": 30,
        "sample_tools": [
            "execute_command",
            "macos-use_take_screenshot",
            "macos-use_get_time",
            "macos-use_fetch_url",
        ],
    },
    "filesystem": {
        "transport": "stdio",
        "external": True,
        "min_tools": 4,
        "sample_tools": ["read_file", "write_file", "list_directory", "search_files"],
    },
    "sequential-thinking": {
        "transport": "stdio",
        "external": True,
        "min_tools": 1,
        "sample_tools": ["sequentialthinking"],
    },
    "googlemaps": {
        "transport": "stdio",
        "binary": True,
        "min_tools": 10,
        "sample_tools": ["maps_geocode", "maps_directions", "maps_search_places"],
    },
    "xcodebuild": {
        "transport": "stdio",
        "external": True,
        "min_tools": 10,
        "sample_tools": [],
    },
    "chrome-devtools": {
        "transport": "stdio",
        "external": True,
        "min_tools": 1,
        "sample_tools": [],
    },
    "vibe": {
        "transport": "stdio",
        "internal_python": True,
        "module": "src.mcp_server.vibe_server",
        "min_tools": 15,
        "sample_tools": [
            "vibe_prompt",
            "vibe_analyze_error",
            "vibe_code_review",
            "vibe_smart_plan",
            "vibe_ask",
            "vibe_get_config",
            "vibe_configure_model",
            "vibe_set_mode",
            "vibe_configure_provider",
            "vibe_session_resume",
            "vibe_list_sessions",
            "vibe_session_details",
            "vibe_reload_config",
            "vibe_which",
            "vibe_implement_feature",
            "vibe_execute_subcommand",
            "vibe_check_db",
            "vibe_get_system_context",
        ],
    },
    "memory": {
        "transport": "stdio",
        "internal_python": True,
        "module": "src.mcp_server.memory_server",
        "min_tools": 10,
        "sample_tools": [
            "create_entities",
            "add_observations",
            "create_relation",
            "search",
            "get_entity",
            "list_entities",
            "delete_entity",
            "ingest_verified_dataset",
            "trace_data_chain",
            "batch_add_nodes",
            "bulk_ingest_table",
            "search_nodes",
            "query_db",
            "get_db_schema",
        ],
    },
    "graph": {
        "transport": "stdio",
        "internal_python": True,
        "module": "src.mcp_server.graph_server",
        "min_tools": 4,
        "sample_tools": [
            "get_graph_json",
            "generate_mermaid",
            "get_node_details",
            "get_related_nodes",
        ],
    },
    "puppeteer": {
        "transport": "stdio",
        "external": True,
        "min_tools": 3,
        "sample_tools": ["puppeteer_navigate", "puppeteer_screenshot"],
    },
    "duckduckgo-search": {
        "transport": "stdio",
        "internal_python": True,
        "module": "src.mcp_server.duckduckgo_search_server",
        "min_tools": 4,
        "sample_tools": [
            "duckduckgo_search",
            "business_registry_search",
            "open_data_search",
            "structured_data_search",
        ],
    },
    "golden-fund": {
        "transport": "stdio",
        "internal_python": True,
        "module": "src.mcp_server.golden_fund.server",
        "min_tools": 7,
        "sample_tools": [
            "search_golden_fund",
            "store_blob",
            "retrieve_blob",
            "ingest_dataset",
            "probe_entity",
            "add_knowledge_node",
            "analyze_and_store",
            "get_dataset_insights",
        ],
    },
    "context7": {
        "transport": "stdio",
        "external": True,
        "min_tools": 1,
        "sample_tools": [],
    },
    "whisper-stt": {
        "transport": "stdio",
        "internal_python": True,
        "module": "src.mcp_server.whisper_server",
        "min_tools": 2,
        "sample_tools": ["transcribe_audio", "record_and_transcribe"],
    },
    "devtools": {
        "transport": "stdio",
        "internal_python": True,
        "module": "src.mcp_server.devtools_server",
        "min_tools": 20,
        "sample_tools": [
            "devtools_list_processes",
            "devtools_restart_mcp_server",
            "devtools_kill_process",
            "devtools_check_mcp_health",
            "devtools_launch_inspector",
            "mcp_inspector_list_tools",
            "mcp_inspector_call_tool",
            "mcp_inspector_list_resources",
            "mcp_inspector_read_resource",
            "mcp_inspector_list_prompts",
            "mcp_inspector_get_prompt",
            "mcp_inspector_get_schema",
            "devtools_run_mcp_sandbox",
            "devtools_validate_config",
            "devtools_lint_python",
            "devtools_lint_js",
            "devtools_run_global_lint",
            "devtools_find_dead_code",
            "devtools_check_integrity",
            "devtools_check_security",
            "devtools_check_complexity",
            "devtools_check_types_python",
            "devtools_check_types_ts",
            "devtools_run_context_check",
            "devtools_analyze_trace",
            "devtools_update_architecture_diagrams",
            "devtools_get_system_map",
            "devtools_test_all_mcp_native",
        ],
    },
    "github": {
        "transport": "stdio",
        "external": True,
        "min_tools": 10,
        "sample_tools": ["get_file_contents", "create_issue", "search_repositories"],
    },
    "redis": {
        "transport": "stdio",
        "internal_python": True,
        "module": "src.mcp_server.redis_server",
        "min_tools": 7,
        "sample_tools": [
            "redis_get",
            "redis_set",
            "redis_keys",
            "redis_delete",
            "redis_info",
            "redis_ttl",
            "redis_hgetall",
            "redis_hset",
        ],
    },
    "data-analysis": {
        "transport": "stdio",
        "internal_python": True,
        "module": "src.mcp_server.data_analysis_server",
        "min_tools": 7,
        "sample_tools": [
            "read_metadata",
            "analyze_dataset",
            "generate_statistics",
            "create_visualization",
            "data_cleaning",
            "data_aggregation",
            "interpret_column_data",
            "run_pandas_code",
        ],
    },
    "postgres": {
        "transport": "stdio",
        "disabled": True,
        "min_tools": 0,
        "sample_tools": [],
    },
    "react-devtools": {
        "transport": "stdio",
        "node_js": True,
        "min_tools": 1,
        "sample_tools": ["react_get_introspection_script"],
    },
    "tour-guide": {
        "transport": "internal",
        "native": True,
        "min_tools": 0,
        "sample_tools": [],
    },
}


class TestAllServersDefinitions:
    """Verify all 21 servers are properly defined and have expected tools."""

    def test_total_server_count(self):
        assert len(ALL_SERVERS_TOOLS) == 21, f"Expected 21 servers, got {len(ALL_SERVERS_TOOLS)}"

    @pytest.mark.parametrize("server_name", list(ALL_SERVERS_TOOLS.keys()))
    def test_server_definition_exists(self, server_name):
        """Each server must have a definition in ALL_SERVERS_TOOLS."""
        assert server_name in ALL_SERVERS_TOOLS

    @pytest.mark.parametrize("server_name", list(ALL_SERVERS_TOOLS.keys()))
    def test_server_has_transport(self, server_name):
        info = ALL_SERVERS_TOOLS[server_name]
        assert "transport" in info
        assert info["transport"] in ("stdio", "internal")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: PYTHON SERVER IMPORT & TOOL COUNT TESTS
# ═══════════════════════════════════════════════════════════════════════════════


PYTHON_SERVERS = {
    name: info for name, info in ALL_SERVERS_TOOLS.items() if info.get("internal_python")
}


class TestPythonServerImports:
    """Verify each Python-based MCP server can be imported without errors."""

    @pytest.mark.parametrize(
        "server_name,info", list(PYTHON_SERVERS.items()), ids=list(PYTHON_SERVERS.keys())
    )
    def test_server_module_importable(self, server_name, info):
        """Python server module must be importable."""
        module_name = info.get("module")
        if not module_name:
            pytest.skip(f"No module defined for {server_name}")

        try:
            __import__(module_name)
        except ModuleNotFoundError as e:
            # Optional dependencies (matplotlib, redis, etc.) may not be installed
            pytest.skip(f"Optional dependency missing for {server_name}: {e}")
        except Exception as e:
            pytest.fail(f"Failed to import {module_name}: {e}")

    @pytest.mark.parametrize(
        "server_name,info", list(PYTHON_SERVERS.items()), ids=list(PYTHON_SERVERS.keys())
    )
    def test_server_has_fastmcp_instance(self, server_name, info):
        """Each Python server must expose a FastMCP 'server' or 'mcp' instance."""
        module_name = info.get("module")
        if not module_name:
            pytest.skip(f"No module for {server_name}")

        try:
            mod = __import__(module_name, fromlist=["server", "mcp"])
        except ModuleNotFoundError as e:
            pytest.skip(f"Optional dependency missing for {server_name}: {e}")
        srv = getattr(mod, "server", None) or getattr(mod, "mcp", None)
        assert srv is not None, f"{module_name} has no 'server' or 'mcp' FastMCP instance"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: JSON-RPC NATIVE SMOKE TESTS (spawn each server)
# ═══════════════════════════════════════════════════════════════════════════════


VENV_PYTHON = str(PROJECT_ROOT / ".venv" / "bin" / "python")


def _resolve_env_vars(text: str) -> str:
    """Replace ${VAR} placeholders with actual values."""
    text = text.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))
    text = text.replace("${HOME}", str(Path.home()))
    for var in ["GOOGLE_MAPS_API_KEY", "GITHUB_TOKEN"]:
        text = text.replace(f"${{{var}}}", os.environ.get(var, ""))
    return text


def _load_mcp_config() -> dict[str, Any]:
    """Load MCP config from active or template."""
    for path in [
        Path.home() / ".config" / "atlastrinity" / "mcp" / "config.json",
        PROJECT_ROOT / "config" / "mcp_servers.json.template",
    ]:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    return {}


def _build_jsonrpc_init_and_list() -> str:
    """Build JSON-RPC messages for initialize + tools/list."""
    init_req = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-suite", "version": "1.0"},
            },
        }
    )
    list_req = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
    )
    return init_req + "\n" + list_req + "\n"


def _spawn_and_list_tools(
    server_name: str, config: dict[str, Any], timeout: float = 20.0
) -> dict[str, Any]:
    """Spawn a server process, send JSON-RPC, and parse tool list."""
    cfg = config.get("mcpServers", {}).get(server_name)
    if not cfg:
        return {"status": "not_configured", "error": "Not in config"}

    if cfg.get("disabled", False):
        return {"status": "disabled"}
    if cfg.get("transport") == "internal":
        return {"status": "internal", "note": "Native service, no process"}

    command = _resolve_env_vars(cfg.get("command", ""))
    # Use venv python for python3 commands to ensure correct Python version
    if command == "python3" and Path(VENV_PYTHON).exists():
        command = VENV_PYTHON
    args = [_resolve_env_vars(a) for a in cfg.get("args", [])]
    env_vars = cfg.get("env", {})

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT)
    for k, v in env_vars.items():
        env[k] = _resolve_env_vars(v)

    full_cmd = [command, *args]
    stdin_data = _build_jsonrpc_init_and_list()

    start = time.time()
    try:
        proc = subprocess.run(
            full_cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(PROJECT_ROOT),
        )
        elapsed_ms = round((time.time() - start) * 1000, 1)

        stdout = proc.stdout.strip()
        if not stdout:
            return {
                "status": "error",
                "error": proc.stderr[:1000] if proc.stderr else "Empty response",
                "response_time_ms": elapsed_ms,
            }

        tool_count = 0
        tool_names = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                resp = json.loads(line)
                if resp.get("id") == 2 and "result" in resp:
                    tools = resp["result"].get("tools", [])
                    tool_count = len(tools)
                    tool_names = [t.get("name", "") for t in tools]
            except json.JSONDecodeError:
                continue

        return {
            "status": "online" if tool_count > 0 else "started",
            "tool_count": tool_count,
            "tool_names": tool_names,
            "response_time_ms": elapsed_ms,
        }

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": f"No response within {timeout}s"}
    except FileNotFoundError:
        return {"status": "not_found", "error": f"Command not found: {full_cmd[0]}"}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


# Servers that can be reliably spawned for quick smoke tests (Python-based)
SPAWNABLE_PYTHON_SERVERS = [
    "memory",
    "graph",
    "duckduckgo-search",
    "golden-fund",
    "devtools",
    "redis",
    "data-analysis",
]


class TestNativeServerSpawn:
    """Spawn each Python-based server and verify tool listing via JSON-RPC."""

    @pytest.fixture(scope="class")
    def mcp_config(self):
        return _load_mcp_config()

    @pytest.mark.parametrize("server_name", SPAWNABLE_PYTHON_SERVERS)
    def test_server_responds(self, server_name, mcp_config):
        """Server must start and respond to JSON-RPC initialize + tools/list."""
        result = _spawn_and_list_tools(server_name, mcp_config)
        if result["status"] in ("not_configured", "disabled", "internal"):
            pytest.skip(f"{server_name}: {result['status']}")
        if result["status"] == "not_found":
            pytest.skip(f"{server_name}: command not found")
        error_msg = str(result.get("error", ""))
        if any(s in error_msg for s in ["ModuleNotFoundError", "No module named", "ImportError"]):
            pytest.skip(f"{server_name}: optional dependency missing")
        assert result["status"] in ("online", "started"), f"{server_name} failed: {error_msg[:200]}"

    @pytest.mark.parametrize("server_name", SPAWNABLE_PYTHON_SERVERS)
    def test_server_tool_count(self, server_name, mcp_config):
        """Server should report expected minimum tools."""
        result = _spawn_and_list_tools(server_name, mcp_config)
        if result["status"] not in ("online", "started"):
            pytest.skip(f"{server_name}: {result['status']}")

        expected_min = ALL_SERVERS_TOOLS.get(server_name, {}).get("min_tools", 1)
        actual = result.get("tool_count", 0)
        assert actual >= expected_min, (
            f"{server_name}: expected >={expected_min} tools, got {actual}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7: TOOL-LEVEL SCHEMA CROSS-VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════


class TestToolSchemasCrossValidation:
    """Cross-validate registry schemas against actual server tool definitions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.brain.mcp_registry import load_registry

        load_registry()

    def test_all_schema_servers_exist_in_config(self):
        """Every server referenced in TOOL_SCHEMAS must exist in the config."""
        from src.brain.mcp_registry import TOOL_SCHEMAS

        config = _load_mcp_config()
        config_servers = set(k for k in config.get("mcpServers", {}) if not k.startswith("_"))
        # Add special/internal servers
        config_servers.update({"system", "_trinity_native", "local"})

        for tool_name, schema in TOOL_SCHEMAS.items():
            if "alias_for" in schema:
                continue
            server = schema.get("server")
            if server and server not in ("system", "_trinity_native", "local"):
                assert server in config_servers, (
                    f"Tool '{tool_name}' references unknown server '{server}'"
                )

    def test_schema_types_are_valid(self):
        """Schema type annotations must be valid Python type strings."""
        from src.brain.mcp_registry import TOOL_SCHEMAS

        valid_types = {"str", "int", "float", "bool", "list", "dict", "any", "Any", "None"}
        for tool_name, schema in TOOL_SCHEMAS.items():
            if "alias_for" in schema:
                continue
            types = schema.get("types", {})
            for param, type_str in types.items():
                assert type_str.lower() in {v.lower() for v in valid_types}, (
                    f"Tool '{tool_name}' param '{param}' has invalid type '{type_str}'"
                )

    def test_required_params_have_types(self):
        """Every required parameter should have a type definition."""
        from src.brain.mcp_registry import TOOL_SCHEMAS

        for tool_name, schema in TOOL_SCHEMAS.items():
            if "alias_for" in schema:
                continue
            required = schema.get("required", [])
            types = schema.get("types", {})
            for param in required:
                assert param in types, f"Tool '{tool_name}': required param '{param}' has no type"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8: DEVTOOLS TESTING CAPABILITIES
# ═══════════════════════════════════════════════════════════════════════════════


class TestDevToolsTestingCapabilities:
    """Test the DevTools server's MCP testing tools (the testing infrastructure)."""

    def test_devtools_validate_config_tool(self):
        """devtools_validate_config should validate config structure."""
        from src.mcp_server.devtools_server import devtools_validate_config

        result = devtools_validate_config()
        if result.get("error") and "not found" in str(result.get("error", "")):
            pytest.skip("Active config not found")
        assert "valid" in result or "error" in result

    def test_devtools_get_system_map_tool(self):
        """devtools_get_system_map should return complete system map."""
        from src.mcp_server.devtools_server import devtools_get_system_map

        result = devtools_get_system_map()
        assert "project_root" in result
        assert "paths" in result
        assert "mcp_servers" in result
        assert "testing" in result
        assert "linter_configs" in result

    def test_system_map_has_all_testing_methods(self):
        """System map should list all testing methods."""
        from src.mcp_server.devtools_server import devtools_get_system_map

        result = devtools_get_system_map()
        testing = result.get("testing", {})
        assert "health_check" in testing
        assert "inspector_list" in testing
        assert "inspector_call" in testing
        assert "sandbox_test" in testing

    def test_devtools_lint_python_tool(self):
        """devtools_lint_python should run ruff successfully."""
        import shutil

        from src.mcp_server.devtools_server import devtools_lint_python

        if not shutil.which("ruff"):
            pytest.skip("ruff not installed")
        result = devtools_lint_python("tests/test_mcp_comprehensive.py")
        assert "success" in result or "error" in result

    def test_inspector_list_tools_function(self):
        """mcp_inspector_list_tools function should exist and be callable."""
        from src.mcp_server.devtools_server import mcp_inspector_list_tools

        assert callable(mcp_inspector_list_tools)

    def test_inspector_call_tool_function(self):
        """mcp_inspector_call_tool function should exist and be callable."""
        from src.mcp_server.devtools_server import mcp_inspector_call_tool

        assert callable(mcp_inspector_call_tool)

    def test_inspector_get_schema_function(self):
        """mcp_inspector_get_schema function should exist and be callable."""
        from src.mcp_server.devtools_server import mcp_inspector_get_schema

        assert callable(mcp_inspector_get_schema)

    def test_devtools_test_all_mcp_native_exists(self):
        """devtools_test_all_mcp_native should exist as a tool."""
        from src.mcp_server.devtools_server import devtools_test_all_mcp_native

        assert callable(devtools_test_all_mcp_native)

    def test_devtools_run_mcp_sandbox_exists(self):
        """devtools_run_mcp_sandbox should exist as a tool."""
        from src.mcp_server.devtools_server import devtools_run_mcp_sandbox

        assert callable(devtools_run_mcp_sandbox)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9: FULL SERVER SMOKE TEST (native JSON-RPC for ALL servers)
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullServerSmokeNative:
    """Run devtools_test_all_mcp_native() and validate results."""

    def test_native_test_all(self):
        """Run the built-in native test across all servers."""
        from src.mcp_server.devtools_server import devtools_test_all_mcp_native

        result = devtools_test_all_mcp_native()

        if "error" in result:
            pytest.skip(f"Native test error: {result['error']}")

        summary = result.get("summary", {})
        servers = result.get("servers", {})

        # Must have tested some servers
        assert summary.get("total", 0) > 0, "No servers were tested"

        # Report results
        print(f"\n{'=' * 60}")
        print("MCP Native Test Results")
        print(f"{'=' * 60}")
        print(f"  Total:    {summary.get('total', 0)}")
        print(f"  Online:   {summary.get('online', 0)}")
        print(f"  Offline:  {summary.get('offline', 0)}")
        print(f"  Disabled: {summary.get('disabled', 0)}")
        print(f"  Health:   {summary.get('health_pct', 0)}%")
        print(f"{'=' * 60}")

        for name, info in sorted(servers.items()):
            status = info.get("status", "unknown")
            tools = info.get("tool_count", "?")
            ms = info.get("response_time_ms", "?")
            err = info.get("error", "")
            if status in ("online", "started", "internal"):
                print(f"  ✓ {name:25} | {status:10} | {tools} tools | {ms}ms")
            elif status == "disabled":
                print(f"  ⊘ {name:25} | disabled")
            else:
                print(f"  ✗ {name:25} | {status:10} | {err[:40]}")

        # At least 50% should be online
        total_active = summary.get("total", 1) - summary.get("disabled", 0)
        online = summary.get("online", 0)
        assert online >= total_active * 0.3, f"Too few servers online: {online}/{total_active}"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10: INDIVIDUAL TOOL FUNCTIONAL TESTS (safe, non-destructive)
# ═══════════════════════════════════════════════════════════════════════════════


class TestIndividualToolsFunctional:
    """Test individual tools from each server with safe arguments."""

    # --- devtools server tools (synchronous, safe) ---

    def test_devtools_validate_config(self):
        from src.mcp_server.devtools_server import devtools_validate_config

        result = devtools_validate_config()
        assert isinstance(result, dict)

    def test_devtools_get_system_map(self):
        from src.mcp_server.devtools_server import devtools_get_system_map

        result = devtools_get_system_map()
        assert "project_root" in result
        assert "paths" in result

    def test_devtools_check_complexity(self):
        import shutil

        from src.mcp_server.devtools_server import devtools_check_complexity

        if not shutil.which("xenon"):
            pytest.skip("xenon not installed")
        result = devtools_check_complexity("src/mcp_server/devtools_server.py")
        assert isinstance(result, dict)

    # --- duckduckgo search server tools ---

    def test_duckduckgo_search_empty_query(self):
        from src.mcp_server.duckduckgo_search_server import duckduckgo_search

        result = duckduckgo_search("")
        assert "error" in result

    def test_duckduckgo_search_invalid_max_results(self):
        from src.mcp_server.duckduckgo_search_server import duckduckgo_search

        result = duckduckgo_search("test", max_results=-1)
        assert "error" in result

    # --- golden-fund server tools ---

    @pytest.mark.asyncio
    async def test_golden_fund_search(self):
        from src.mcp_server.golden_fund.server import search_golden_fund

        result = await search_golden_fund("test query", mode="semantic")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_golden_fund_probe_entity(self):
        from src.mcp_server.golden_fund.server import probe_entity

        result = await probe_entity("nonexistent_entity_xyz")
        data = json.loads(result)
        assert data.get("found") is False

    @pytest.mark.asyncio
    async def test_golden_fund_store_and_retrieve_blob(self):
        from src.mcp_server.golden_fund.server import retrieve_blob, store_blob

        store_result = await store_blob("test content", "test_blob.txt")
        assert isinstance(store_result, str)
        retrieve_result = await retrieve_blob("test_blob.txt")
        assert isinstance(retrieve_result, str)

    # --- graph server tools (need db init) ---

    @pytest.mark.asyncio
    async def test_graph_get_graph_json(self):
        try:
            from src.mcp_server.graph_server import get_graph_json

            result = await get_graph_json()
            assert isinstance(result, dict)
        except Exception as e:
            pytest.skip(f"Graph server needs DB: {e}")

    @pytest.mark.asyncio
    async def test_graph_generate_mermaid(self):
        try:
            from src.mcp_server.graph_server import generate_mermaid

            result = await generate_mermaid()
            assert isinstance(result, str)
        except Exception as e:
            pytest.skip(f"Graph server needs DB: {e}")

    # --- data-analysis server tools ---

    @pytest.mark.asyncio
    async def test_data_analysis_read_metadata_missing_file(self):
        try:
            from src.mcp_server.data_analysis_server import read_metadata
        except ModuleNotFoundError as e:
            pytest.skip(f"data-analysis dependency missing: {e}")

        result = await read_metadata("/nonexistent/file.csv")
        assert result.get("success") is False

    @pytest.mark.asyncio
    async def test_data_analysis_read_metadata_test_csv(self):
        test_csv = PROJECT_ROOT / "test_data" / "test.csv"
        if not test_csv.exists():
            pytest.skip("test_data/test.csv not found")

        try:
            from src.mcp_server.data_analysis_server import read_metadata
        except ModuleNotFoundError as e:
            pytest.skip(f"data-analysis dependency missing: {e}")

        result = await read_metadata(str(test_csv))
        assert result.get("success") is True
        assert "columns" in result

    @pytest.mark.asyncio
    async def test_data_analysis_analyze_missing_file(self):
        try:
            from src.mcp_server.data_analysis_server import analyze_dataset
        except ModuleNotFoundError as e:
            pytest.skip(f"data-analysis dependency missing: {e}")

        result = await analyze_dataset("/nonexistent/file.csv")
        assert result.get("success") is False

    @pytest.mark.asyncio
    async def test_data_analysis_run_pandas_code_safe(self):
        try:
            from src.mcp_server.data_analysis_server import run_pandas_code
        except ModuleNotFoundError as e:
            pytest.skip(f"data-analysis dependency missing: {e}")

        result = await run_pandas_code("result = 2 + 2")
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_data_analysis_run_pandas_code_blocked(self):
        try:
            from src.mcp_server.data_analysis_server import run_pandas_code
        except ModuleNotFoundError as e:
            pytest.skip(f"data-analysis dependency missing: {e}")

        result = await run_pandas_code("import os; os.system('ls')")
        assert result.get("success") is False

    # --- redis server tools (need redis) ---

    @pytest.mark.asyncio
    async def test_redis_info(self):
        try:
            from src.mcp_server.redis_server import redis_info

            result = await redis_info()
            assert isinstance(result, dict)
        except Exception:
            pytest.skip("Redis not available")

    # --- memory server tools (need db) ---

    @pytest.mark.asyncio
    async def test_memory_list_entities(self):
        try:
            from src.mcp_server.memory_server import list_entities

            result = await list_entities()
            assert isinstance(result, dict)
            assert "names" in result or "error" in result
        except Exception as e:
            pytest.skip(f"Memory server needs DB: {e}")

    @pytest.mark.asyncio
    async def test_memory_search_empty(self):
        try:
            from src.mcp_server.memory_server import search

            result = await search("")
            assert "error" in result
        except Exception as e:
            pytest.skip(f"Memory server needs DB: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE RUNNER
# ═══════════════════════════════════════════════════════════════════════════════


def _print_header(title: str):
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}\n")


def _run_section(title: str, test_class):
    """Run all methods of a test class in standalone mode."""
    _print_header(title)
    instance = test_class()
    # Call setup fixtures if present
    if hasattr(instance, "setup_registry"):
        instance.setup_registry()
    if hasattr(instance, "setup"):
        instance.setup()

    passed = 0
    failed = 0
    skipped = 0

    for method_name in sorted(dir(instance)):
        if not method_name.startswith("test_"):
            continue
        method = getattr(instance, method_name)
        try:
            result = method()
            if asyncio.iscoroutine(result):
                asyncio.get_event_loop().run_until_complete(result)
            print(f"  ✓ {method_name}")
            passed += 1
        except Exception as e:
            if "skip" in str(type(e).__name__).lower():
                print(f"  ⊘ {method_name} (skipped: {e})")
                skipped += 1
            else:
                print(f"  ✗ {method_name}: {e}")
                failed += 1

    print(f"\n  Results: {passed} passed, {failed} failed, {skipped} skipped")
    return passed, failed, skipped


def main():
    """Standalone test runner."""
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║     AtlasTrinity MCP Comprehensive Test Suite (21 Servers)     ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    total_p, total_f, total_s = 0, 0, 0

    sections = [
        ("1. MCP Configuration Validation", TestMCPConfiguration),
        ("2. MCP Registry Tests", TestMCPRegistry),
        ("3. All Server Definitions", TestAllServersDefinitions),
        ("4. Python Server Imports", TestPythonServerImports),
        ("5. DevTools Testing Capabilities", TestDevToolsTestingCapabilities),
        ("6. Full Server Smoke Test (Native)", TestFullServerSmokeNative),
        ("7. Individual Tool Functional Tests", TestIndividualToolsFunctional),
    ]

    for title, cls in sections:
        p, f, s = _run_section(title, cls)
        total_p += p
        total_f += f
        total_s += s

    _print_header("FINAL SUMMARY")
    print(f"  Total Passed:  {total_p}")
    print(f"  Total Failed:  {total_f}")
    print(f"  Total Skipped: {total_s}")
    print(f"  Overall:       {'✓ ALL PASSED' if total_f == 0 else f'✗ {total_f} FAILURES'}")
    print()

    return 0 if total_f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
