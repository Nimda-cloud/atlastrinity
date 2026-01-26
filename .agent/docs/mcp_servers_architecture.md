# MCP Servers Architecture - Complete Reference

## Overview

AtlasTrinity використовує **17 MCP серверів** (16 активних, 1 disabled) для взаємодії з системою, даними та зовнішніми сервісами.

**Останнє оновлення:** 2026-01-26  
**Версія конфігурації:** 4.6

---

## Table of Contents

1. [Server Inventory](#server-inventory)
2. [Configuration Files](#configuration-files)
3. [Tool Selection & Execution Pipeline](#tool-selection--execution-pipeline)
4. [Server Details by Tier](#server-details-by-tier)
5. [Agent Access Matrix](#agent-access-matrix)
6. [Tool Routing & Dispatch](#tool-routing--dispatch)

---

## Server Inventory

### Active Servers: 16

| # | Server Name | Tier | Type | Tools Count | Agents |
|---|-------------|------|------|-------------|--------|
| 1 | macos-use | 1 | Swift Binary | 35+ | Tetyana, Grisha |
| 2 | filesystem | 1 | NPX | ~8 | Tetyana, Grisha |
| 3 | sequential-thinking | 1 | Bunx | 1 | Atlas, Tetyana, Grisha |
| 4 | vibe | 2 | Python | 12 | Atlas, Tetyana, Grisha |
| 5 | memory | 2 | Python | 9 | Atlas, Tetyana, Grisha |
| 6 | graph | 2 | Python | 4 | Atlas, Tetyana, Grisha |
| 7 | duckduckgo-search | 2 | Python | 2 | Tetyana, Grisha |
| 8 | golden-fund | 2 | Python | 8 | Atlas, Tetyana, Grisha |
| 9 | whisper-stt | 2 | Python | 1 | Tetyana |
| 10 | devtools | 2 | Python | 6 | Grisha, Tetyana |
| 11 | github | 2 | NPX | ~12 | Atlas, Tetyana, Grisha |
| 12 | redis | 2 | Python | 5 | Atlas, Tetyana, Grisha |
| 13 | data-analysis | 2 | Python | 10 | Atlas, Tetyana, Grisha |
| 14 | puppeteer | 3 | NPX | ~8 | Tetyana, Grisha |
| 15 | context7 | 3 | NPX | ~3 | Atlas, Tetyana, Grisha |
| 16 | chrome-devtools | 4 | Bunx | ~5 | Tetyana |

### Disabled Servers: 1

| # | Server Name | Tier | Reason |
|---|-------------|------|--------|
| 17 | postgres | 3 | Experimental, requires PostgreSQL 17 |

**Total Tools Available:** ~130+ tools across all servers

---

## Configuration Files

### 1. Primary Configuration

#### `config/mcp_servers.json.template`
- **Purpose:** Template for MCP server definitions
- **Location:** `${PROJECT_ROOT}/config/mcp_servers.json.template`
- **Synced to:** `~/.config/atlastrinity/mcp/mcp_servers.json`
- **Format:** JSON
- **Content:**
  - Server commands and arguments
  - Connection timeouts
  - Environment variables
  - Tier assignments
  - Agent access permissions
  - Enable/disable flags

#### `config/config.yaml.template`
- **Purpose:** Main system configuration with MCP settings
- **Location:** `${PROJECT_ROOT}/config/config.yaml.template`
- **Synced to:** `~/.config/atlastrinity/config.yaml`
- **Content:**
  - MCP server enable/disable flags
  - Connection settings (retry_attempts, connection_timeout)
  - Sequential-thinking model configuration
  - Vibe workspace paths
  - Server-specific settings

#### `config/behavior_config.yaml.template`
- **Purpose:** Tool routing and behavior rules
- **Location:** `${PROJECT_ROOT}/config/behavior_config.yaml.template`
- **Synced to:** `~/.config/atlastrinity/behavior_config.yaml`
- **Content:**
  - Tool routing mappings (synonyms → servers)
  - Task classification rules
  - Strategy selection logic
  - Tool fallback chains

### 2. Code Registry Files

#### `src/brain/mcp_registry.py`
- **Purpose:** Central registry for MCP servers and tool schemas
- **Key Exports:**
  - `SERVER_CATALOG` - Server definitions loaded from JSON
  - `TOOL_SCHEMAS` - Tool parameter schemas
  - Protocol documentation (VOICE, SEARCH, STORAGE, etc.)
- **Data Sources:**
  - `src/brain/data/mcp_catalog.json`
  - `src/brain/data/tool_schemas.json`
  - `src/brain/data/*.txt` (protocols)

#### `src/brain/tool_dispatcher.py`
- **Purpose:** Dynamic tool routing and dispatch logic
- **Functions:**
  - `resolve_server_for_action()` - Maps tool name to server
  - `get_available_tools()` - Lists tools for current context
  - Server synonym resolution
  - Fallback chain execution

#### `src/brain/mcp_manager.py`
- **Purpose:** MCP server lifecycle management
- **Functions:**
  - Server connection/disconnection
  - Tool execution via MCP protocol
  - Health monitoring
  - Error handling and retries

### 3. Agent-Specific Files

#### Atlas (`src/brain/agents/atlas.py`)
- **Tool Access:** All 16 active servers
- **Primary Use:** Planning, memory search, Vibe consultation
- **Model:** `gpt-4.1` (from config)

#### Tetyana (`src/brain/agents/tetyana.py`)
- **Tool Access:** 14 servers (excludes context7, redis read-only)
- **Primary Use:** Execution, macOS interaction, file operations
- **Model:** `gpt-4.1` (execution)

#### Grisha (`src/brain/agents/grisha.py`)
- **Tool Access:** All 16 active servers
- **Primary Use:** Verification, auditing, vision analysis
- **Models:** 
  - Phase 1: `raptor-mini` (strategy)
  - Phase 2: `gpt-4.1` (execution)
  - Phase 3: `raptor-mini` (verdict), `gpt-4o` (vision)

---

## Tool Selection & Execution Pipeline

### Phase 1: Intent Detection
**File:** `src/brain/behavior_engine.py`

```yaml
# From behavior_config.yaml
intent_detection:
  simple_chat: [keywords matching]
  info_query: [tool requirements]
  complex_task: [planning needed]
```

### Phase 2: Tool Routing
**File:** `src/brain/tool_dispatcher.py`

**Routing Logic:**
```
User Request
    ↓
Intent Detection (behavior_engine.py)
    ↓
Synonym Resolution (tool_dispatcher.py)
    ↓
Server Selection (tool_routing in behavior_config.yaml)
    ↓
Tool Schema Lookup (mcp_registry.py → TOOL_SCHEMAS)
    ↓
Execute via MCP Manager
```

**Example Routing:**
```python
# From behavior_config.yaml
tool_routing:
  terminal:
    synonyms: [bash, zsh, execute, run]
    priority_server: macos-use
    tool_mapping:
      terminal: execute_command
      
  filesystem:
    synonyms: [file, read_file, write_file]
    priority_server: filesystem
```

### Phase 3: Tool Execution
**File:** `src/brain/mcp_manager.py`

**Execution Flow:**
```
Tool Call Request
    ↓
Server Health Check
    ↓
MCP Protocol Call (stdin/stdout)
    ↓
Result Parsing
    ↓
Error Handling (retry with backoff)
    ↓
Return to Agent
```

### Phase 4: Agent Processing

**Tetyana (Executor):**
```python
# Phase 2 model: gpt-4.1
1. Receive tool name + arguments
2. Validate against TOOL_SCHEMAS
3. Execute via mcp_manager
4. Return result to orchestrator
```

**Grisha (Verifier):**
```python
# Phase 1: strategy_model (raptor-mini)
1. Analyze what to verify
2. Select verification tools

# Phase 2: model (gpt-4.1)
3. Execute MCP tools
4. Collect evidence

# Phase 3: verdict_model (raptor-mini), vision_model (gpt-4o)
5. Analyze evidence
6. Form verdict
```

---

## Server Details by Tier

### TIER 1: Core System (Must-Have)

#### 1. macos-use
- **Type:** Swift binary (compiled native)
- **Path:** `vendor/mcp-server-macos-use/.build/release/mcp-server-macos-use`
- **Tools:** 35+ (GUI, Terminal, Vision, System)
- **Key Features:**
  - Universal macOS control
  - Accessibility API integration
  - Screen recording & OCR
  - AppleScript execution
  - Calendar, Reminders, Notes, Mail, Finder
  - Spotlight search
  - Clipboard operations
- **Permissions Required:**
  - Accessibility: `true`
  - Screen Recording: `true`
- **Agents:** Tetyana (primary executor), Grisha (verification)
- **Timeout:** 3600s

#### 2. filesystem
- **Type:** Official NPX package
- **Package:** `@modelcontextprotocol/server-filesystem`
- **Tools:** ~8 (read, write, list, search, move, etc.)
- **Key Features:**
  - File operations (CRUD)
  - Directory traversal
  - Search capabilities
- **Security:**
  - `deny_write_repo: true`
  - `repo_write_allowed_subdir: .atlastrinity_runtime`
- **Allowed Paths:** `${HOME}`, `/tmp`
- **Agents:** Tetyana, Grisha
- **Timeout:** 60s

#### 3. sequential-thinking
- **Type:** Official Bunx package
- **Package:** `@modelcontextprotocol/server-sequential-thinking`
- **Tools:** 1 (`sequentialthinking`)
- **Key Features:**
  - Dynamic thought sequences
  - Chain-of-thought reasoning
  - Problem decomposition
- **Environment:**
  - `MAX_HISTORY_SIZE: 1000`
- **Model Configuration:**
  - Uses `models.reasoning` (raptor-mini)
  - Configurable in `config.yaml`: `mcp.sequential_thinking.model`
- **Critical For:** Grisha verification (Phase 1 strategy, Phase 3 verdict)
- **Agents:** Atlas, Tetyana, Grisha
- **Timeout:** 60s

---

### TIER 2: High Priority (Recommended)

#### 4. vibe
- **Type:** Python MCP server (internal)
- **Module:** `src.mcp_server.vibe_server`
- **Tools:** 12
  1. `vibe_prompt` - General coding assistance
  2. `vibe_analyze_error` - Debug error analysis
  3. `vibe_implement_feature` - Feature implementation
  4. `vibe_check_db` - SQL database inspection
  5. `vibe_get_system_context` - System state analysis
  6. `vibe_code_review` - Code quality review
  7. `vibe_smart_plan` - Architecture planning
  8. `vibe_ask` - Q&A about codebase
  9. `vibe_execute_subcommand` - Execute vibe CLI commands
  10. `vibe_which` - Check active model
  11. `vibe_list_sessions` - List conversation sessions
  12. `vibe_session_details` - Get session info
- **Model:** `devstral-2` (Mistral, configured in `vibe_config.toml`)
- **Mode:** Programmatic CLI (`--output json`), not interactive TUI
- **Workspace:** `${CONFIG_ROOT}/vibe_workspace`
- **Max Output:** 500KB
- **Agents:** Atlas (consultation), Tetyana (code tasks), Grisha (verification)
- **Timeout:** 3600s

#### 5. memory
- **Type:** Python MCP server (internal)
- **Module:** `src.mcp_server.memory_server`
- **Storage:** SQLite + ChromaDB
- **Tools:** 9
  1. `create_entities` - Create knowledge entities
  2. `add_observations` - Add facts to entities
  3. `create_relation` - Link entities
  4. `search` - Semantic search
  5. `get_entity` - Retrieve entity details
  6. `list_entities` - List all entities
  7. `delete_entity` - Remove entity
  8. `ingest_verified_dataset` - Bulk data import
  9. `trace_data_chain` - Provenance tracking
- **Database Paths:**
  - SQLite: `${CONFIG_ROOT}/memory/knowledge.db`
  - ChromaDB: `${CONFIG_ROOT}/memory/chroma`
- **Agents:** Atlas (memory management), Tetyana (data storage), Grisha (verification)
- **Timeout:** 60s

#### 6. graph
- **Type:** Python MCP server (internal)
- **Module:** `src.mcp_server.graph_server`
- **Tools:** 4
  1. `generate_mermaid` - Mermaid diagram generation
  2. `get_node_details` - Node information
  3. `get_related_nodes` - Graph traversal
  4. `get_graph_json` - Export graph as JSON
- **Use Cases:** Knowledge graph visualization, relationship mapping
- **Agents:** Atlas, Tetyana, Grisha
- **Timeout:** 60s

#### 7. duckduckgo-search
- **Type:** Python MCP server (internal)
- **Module:** `src.mcp_server.duckduckgo_search_server`
- **Tools:** 2
  1. `duckduckgo_search` - General web search
  2. `business_registry_search` - Ukrainian business registry (ЄДРПОУ)
- **Method:** HTML screen scraping (no API key required)
- **Special Features:**
  - Ukrainian business lookup (YouControl, OpenDataBot)
  - Open data portal integration (data.gov.ua)
- **Agents:** Tetyana (information gathering), Grisha (verification)
- **Timeout:** 60s

#### 8. golden-fund
- **Type:** Python MCP server (internal)
- **Module:** `src.mcp_server.golden_fund.server`
- **Tools:** 8
  1. `search_golden_fund` - Semantic search in knowledge base
  2. `probe_entity` - Deep entity analysis
  3. `ingest_dataset` - Import structured data
  4. `add_knowledge_node` - Add knowledge nodes
  5. `analyze_and_store` - Analyze and persist insights
  6. `get_dataset_insights` - Dataset metadata
  7. `store_blob` - Store binary data
  8. `retrieve_blob` - Retrieve binary data
- **Storage:** `${CONFIG_ROOT}/data/golden_fund/`
- **Use Cases:** Long-term knowledge storage, dataset analysis
- **Agents:** Atlas, Tetyana, Grisha
- **Timeout:** 60s

#### 9. whisper-stt
- **Type:** Python MCP server (internal)
- **Module:** `src.mcp_server.whisper_server`
- **Tools:** 1 (`transcribe`)
- **Model:** `large-v3` (configurable in `config.yaml`)
- **Language:** Ukrainian (uk)
- **Backend Options:**
  - Local Whisper (faster-whisper)
  - Brain API (remote)
- **Use Cases:** Voice recording transcription
- **Agents:** Tetyana (voice input)
- **Timeout:** 60s

#### 10. devtools
- **Type:** Python MCP server (internal)
- **Module:** `src.mcp_server.devtools_server`
- **Tools:** 6
  1. `devtools_lint_python` - Ruff linter
  2. `devtools_lint_js` - Oxlint (JS/TS)
  3. `devtools_find_unused` - Knip (dead code)
  4. `devtools_typecheck` - Pyrefly (Python types)
  5. `devtools_launch_inspector` - MCP Inspector UI
  6. `devtools_check_mcp_health` - Server health check
- **Enabled Tools:** All (ruff, oxlint, knip, pyrefly, inspector, health_check)
- **Use Cases:** Code quality, linting, health monitoring
- **Agents:** Grisha (code verification), Tetyana (code tasks)
- **Timeout:** 60s

#### 11. github
- **Type:** Official NPX package
- **Package:** `@modelcontextprotocol/server-github`
- **Tools:** ~12 (PRs, Issues, Search, File Ops)
- **Environment:** `GITHUB_TOKEN` (required)
- **Key Features:**
  - Pull Request management
  - Issue tracking
  - Repository search
  - File operations
  - Branch management
- **Agents:** Atlas (planning), Tetyana (execution), Grisha (verification)
- **Timeout:** 60s

#### 12. redis
- **Type:** Python MCP server (internal)
- **Module:** `src.mcp_server.redis_server`
- **Tools:** 5
  1. `redis_get` - Get key value
  2. `redis_set` - Set key value
  3. `redis_keys` - List keys
  4. `redis_delete` - Delete key
  5. `redis_info` - Server info
- **URL:** `redis://localhost:6379/0`
- **Use Cases:** State inspection, session management, debugging
- **Agents:** Atlas (state management), Tetyana (caching), Grisha (verification)
- **Timeout:** 60s

#### 13. data-analysis
- **Type:** Python MCP server (internal)
- **Module:** `src.mcp_server.data_analysis_server`
- **Tools:** 10
  1. `read_metadata` - File metadata inspection
  2. `analyze_dataset` - Statistical analysis
  3. `generate_statistics` - Descriptive stats
  4. `create_visualization` - Chart generation
  5. `data_cleaning` - Data preprocessing
  6. `data_aggregation` - Group-by operations
  7. `interpret_column_data` - Column semantics
  8. `run_pandas_code` - Execute Pandas code
  9. `correlation_analysis` - Correlation matrix
  10. `outlier_detection` - Anomaly detection
- **Supported Formats:** CSV, Excel, JSON, Parquet
- **Engine:** Pandas-based
- **Agents:** Atlas (analysis planning), Tetyana (data processing), Grisha (result verification)
- **Timeout:** 60s

---

### TIER 3: Additional (Optional)

#### 14. puppeteer
- **Type:** Official NPX package
- **Package:** `@modelcontextprotocol/server-puppeteer`
- **Tools:** ~8 (navigation, screenshots, interaction, JS execution)
- **Mode:** Headless browser
- **Environment:** `PUPPETEER_ALLOW_DANGEROUS: true`
- **Key Features:**
  - Web navigation
  - Element interaction
  - Screenshot capture
  - JavaScript execution
  - Form filling
- **Use Cases:** Web scraping, automation, weather checks, info gathering
- **Agents:** Tetyana (web tasks), Grisha (verification)
- **Timeout:** 60s

#### 15. context7
- **Type:** External NPX package
- **Package:** `c7-mcp-server`
- **Tools:** ~3 (documentation lookup)
- **Purpose:** Context-aware documentation for libraries and frameworks
- **Use Cases:** API documentation, usage examples
- **Agents:** Atlas, Tetyana, Grisha
- **Timeout:** 60s

---

### TIER 4: Specialized (Debug)

#### 16. chrome-devtools
- **Type:** External Bunx package
- **Package:** `chrome-devtools-mcp`
- **Tools:** ~5 (Chrome DevTools Protocol)
- **Purpose:** Browser debugging and automation
- **Use Cases:** Advanced web debugging, performance profiling
- **Agents:** Tetyana (web debugging)
- **Timeout:** 60s

---

### Disabled Servers

#### 17. postgres (DISABLED)
- **Type:** Python MCP server (internal)
- **Module:** `src.mcp_server.postgres_server`
- **Status:** Experimental
- **Requirement:** Local PostgreSQL 17 installation
- **Use Cases:** Structured data querying beyond SQLite capabilities
- **Agents:** Tetyana, Grisha (when enabled)
- **Note:** Disabled by default, enable only when needed

---

## Agent Access Matrix

| Server | Atlas | Tetyana | Grisha | Notes |
|--------|-------|---------|--------|-------|
| macos-use | ❌ | ✅ | ✅ | Tetyana primary, Grisha verification |
| filesystem | ❌ | ✅ | ✅ | Execution + verification |
| sequential-thinking | ✅ | ✅ | ✅ | All agents (reasoning) |
| vibe | ✅ | ✅ | ✅ | All agents (code assistance) |
| memory | ✅ | ✅ | ✅ | All agents (knowledge) |
| graph | ✅ | ✅ | ✅ | All agents (visualization) |
| duckduckgo-search | ❌ | ✅ | ✅ | Web search + business registry |
| golden-fund | ✅ | ✅ | ✅ | All agents (knowledge base) |
| whisper-stt | ❌ | ✅ | ❌ | Tetyana only (voice input) |
| devtools | ❌ | ✅ | ✅ | Code quality (Grisha primary) |
| github | ✅ | ✅ | ✅ | All agents (Git operations) |
| redis | ✅ | ✅ | ✅ | All agents (state) |
| data-analysis | ✅ | ✅ | ✅ | All agents (data tasks) |
| puppeteer | ❌ | ✅ | ✅ | Web automation |
| context7 | ✅ | ✅ | ✅ | Documentation lookup |
| chrome-devtools | ❌ | ✅ | ❌ | Tetyana only (browser debug) |
| postgres | ❌ | ✅ | ✅ | Disabled by default |

**Legend:**
- ✅ Has access
- ❌ No access

---

## Tool Routing & Dispatch

### Key Files Regulating Tool Selection

#### 1. `config/behavior_config.yaml.template`
**Section: `tool_routing`**

Defines synonym mappings and routing rules:
```yaml
tool_routing:
  terminal:
    synonyms: [bash, zsh, terminal, execute, run, command]
    priority_server: macos-use
    fallback_server: null
    tool_mapping:
      terminal: execute_command
      execute: execute_command
```

#### 2. `src/brain/tool_dispatcher.py`
**Key Functions:**

```python
def resolve_server_for_action(action: str, context: dict) -> tuple[str, str]:
    """
    Maps action name to (server, tool) tuple.
    
    Steps:
    1. Check exact match in TOOL_SCHEMAS
    2. Apply synonym resolution from behavior_config
    3. Check routing rules (pattern matching)
    4. Apply fallback chain
    5. Return (server_name, tool_name)
    """
```

#### 3. `src/brain/mcp_registry.py`
**Data Sources:**

- `SERVER_CATALOG` - Loaded from `src/brain/data/mcp_catalog.json`
- `TOOL_SCHEMAS` - Loaded from `src/brain/data/tool_schemas.json`

**Provides:**
- Tool parameter validation
- Server capability discovery
- Protocol documentation

#### 4. `src/brain/mcp_manager.py`
**Key Functions:**

```python
async def call_tool(server_name: str, tool_name: str, arguments: dict) -> dict:
    """
    Executes MCP tool via server connection.
    
    Steps:
    1. Validate server is connected
    2. Format MCP protocol request
    3. Send via stdin, read from stdout
    4. Parse response
    5. Handle errors (retry with backoff)
    6. Return result
    """
```

### Tool Selection Algorithm

**Input:** User request or agent action

**Step 1: Intent Classification** (`behavior_engine.py`)
```
User: "Find all Python files"
  ↓
Intent: info_query (requires tools)
```

**Step 2: Synonym Resolution** (`tool_dispatcher.py`)
```
Action: "find"
  ↓
Synonyms: [find, search, grep, list]
  ↓
Server: filesystem or macos-use
```

**Step 3: Server Selection** (`tool_routing` in `behavior_config.yaml`)
```
Task Type: file_tasks
  ↓
Recommended Servers: [filesystem, macos-use]
  ↓
Priority: filesystem (Tier 1)
```

**Step 4: Tool Mapping** (`tool_dispatcher.py`)
```
Server: filesystem
Action: find
  ↓
Tool: list_directory (with recursive option)
```

**Step 5: Schema Validation** (`mcp_registry.py → TOOL_SCHEMAS`)
```
Tool: list_directory
Required Args: {path: str}
Optional Args: {recursive: bool, pattern: str}
  ↓
Validate user arguments
```

**Step 6: Execution** (`mcp_manager.py`)
```
Server: filesystem
Tool: list_directory
Args: {path: "/Users/hawk", recursive: true, pattern: "*.py"}
  ↓
MCP Protocol Call
  ↓
Result: [list of files]
```

---

## Configuration Sync

### Sync Script
```bash
npm run config:sync         # Sync templates to active configs (with backup)
npm run config:sync -- --force  # Force overwrite existing configs
```

### Template Sources
- `config/config.yaml.template` → `~/.config/atlastrinity/config.yaml`
- `config/behavior_config.yaml.template` → `~/.config/atlastrinity/behavior_config.yaml`
- `config/mcp_servers.json.template` → `~/.config/atlastrinity/mcp/mcp_servers.json`
- `config/vibe_config.toml.template` → `~/.config/atlastrinity/vibe_config.toml`

---

## Summary Statistics

- **Total Servers:** 17 (16 active, 1 disabled)
- **Total Tools:** ~130+
- **Configuration Files:** 8 primary files
- **Code Files:** 12+ files regulating tool selection/execution
- **Tiers:** 4 (1=Core, 2=High Priority, 3=Additional, 4=Specialized)
- **Python Servers:** 11
- **NPX/Bunx Servers:** 5
- **Swift Servers:** 1 (macos-use)

### Tool Distribution by Category
- **macOS Control:** 35+ (macos-use)
- **Filesystem:** 8 (filesystem)
- **Code Assistance:** 12 (vibe)
- **Memory/Knowledge:** 9 (memory) + 8 (golden-fund)
- **Data Analysis:** 10 (data-analysis)
- **Search:** 2 (duckduckgo) + 8 (puppeteer)
- **Developer Tools:** 6 (devtools)
- **Version Control:** 12 (github)
- **State Management:** 5 (redis)
- **Reasoning:** 1 (sequential-thinking)
- **Visualization:** 4 (graph)
- **Voice:** 1 (whisper-stt)
- **Browser:** 8 (puppeteer) + 5 (chrome-devtools)
- **Documentation:** 3 (context7)

---

## Related Documentation

- **3-Phase Verification:** `.agent/docs/grisha_3phase_architecture.md`
- **Model Configuration:** `config/config.yaml.template` (models section)
- **Behavior Rules:** `config/behavior_config.yaml.template`
- **Vibe CLI:** `config/vibe_config.toml.template`

---

**End of MCP Servers Architecture Reference**
