# MCP Servers Architecture v4.7 - Visual Diagram

> **Auto-rendered**: This diagram automatically renders in GitHub, VSCode (with Mermaid extension), and other Markdown viewers.

## Complete Execution Flow

```mermaid
flowchart TD
    Start([User Request]) --> Intent[Intent Detection<br/>behavior_engine.py]
    
    Intent --> |simple_chat| Direct[Direct Response]
    Intent --> |info_query| Route[Tool Routing]
    Intent --> |complex_task| Route
    
    Route --> Synonym[Synonym Resolution<br/>tool_dispatcher.py]
    Synonym --> Server[Server Selection<br/>behavior_config.yaml]
    Server --> Schema[Schema Lookup 🆕<br/>mcp_registry.py<br/>CACHED]
    
    Schema --> Validate{Validation}
    Validate --> |missing args| AutoFill[Auto-fill Arguments 🆕<br/>query ← question<br/>prompt ← query]
    AutoFill --> Validate
    
    Validate --> |valid| Convert[Type Conversion 🆕<br/>str/int/float/bool<br/>list: JSON + comma<br/>dict: JSON]
    Validate --> |invalid| Error1[Return Error]
    
    Convert --> Metrics1[Start Metrics 🆕<br/>Track start time]
    Metrics1 --> Session[Get/Create Session<br/>mcp_manager.py]
    
    Session --> |connected| Execute[MCP Protocol Call<br/>session.call_tool]
    Session --> |failed| Retry{Connection<br/>Error?}
    
    Execute --> |success| Metrics2[Track Duration 🆕<br/>Log if >5s]
    Execute --> |error| ErrorHandle{Error Type}
    
    ErrorHandle --> |connection| Backoff[Exponential Backoff 🆕<br/>Retry 1: 0.5s<br/>Retry 2: 1.0s]
    Backoff --> Cleanup[Session Cleanup 🆕]
    Cleanup --> Session
    
    ErrorHandle --> |other| Error2[Detailed Error 🆕<br/>server, tool, context]
    
    Metrics2 --> Result[Return Result]
    Error1 --> Result
    Error2 --> Result
    Direct --> Result
    Result --> End([Agent Processing])
    
    style Intent fill:#e1f5ff
    style Schema fill:#fff4e1
    style AutoFill fill:#e1ffe1
    style Convert fill:#e1ffe1
    style Metrics1 fill:#ffe1f5
    style Metrics2 fill:#ffe1f5
    style Backoff fill:#ffe1e1
    style Cleanup fill:#ffe1e1
```

## Phase 1: Intent Detection

```mermaid
graph LR
    subgraph "behavior_engine.py"
        A[Load Config] --> B[Parse Keywords]
        B --> C{Match Intent}
        C --> |chat| D[simple_chat]
        C --> |query| E[info_query]
        C --> |task| F[complex_task]
    end
    
    G[behavior_config.yaml] -.->|rules| A
    
    style A fill:#e1f5ff
    style B fill:#e1f5ff
    style C fill:#e1f5ff
```

## Phase 2: Tool Routing & Validation

```mermaid
graph TB
    subgraph "tool_dispatcher.py"
        A[Tool Name] --> B[Synonym Map]
        B --> C[Server Selection]
        C --> D[Schema Lookup]
        D --> E{Has Schema?}
        E --> |yes| F[Validate Args]
        E --> |no| G[Pass Through]
        F --> H{Missing Args?}
        H --> |yes| I[Auto-fill 🆕<br/>query/prompt]
        H --> |no| J[Type Convert 🆕]
        I --> K{Still Missing?}
        K --> |yes| L[Error]
        K --> |no| J
        J --> M[Ready for Execution]
    end
    
    N[mcp_registry.py<br/>Cache 🆕] -.->|cached lookup| D
    O[tool_schemas.json] -.->|schema data| D
    
    style I fill:#e1ffe1
    style J fill:#e1ffe1
    style N fill:#fff4e1
```

## Phase 3: Tool Execution with Resilience

```mermaid
sequenceDiagram
    participant D as Dispatcher
    participant M as MCPManager
    participant S as Session
    participant Server as MCP Server
    
    D->>M: call_tool(server, tool, args)
    activate M
    M->>M: Start Metrics 🆕
    M->>S: get_session(server)
    
    alt Session Exists
        S-->>M: Return session
    else No Session
        S->>Server: Connect
        Server-->>S: Connection OK
        S-->>M: New session
    end
    
    M->>Server: call_tool(tool, args)
    
    alt Success
        Server-->>M: Result
        M->>M: Track Duration 🆕
        M-->>D: Return result
    else Connection Error
        Server--xM: Connection Lost
        M->>M: Cleanup Session 🆕
        M->>M: Wait 0.5s (Retry 1) 🆕
        M->>Server: Reconnect
        
        alt Retry Success
            Server-->>M: Result
            M-->>D: Return result
        else Retry Failed
            M->>M: Wait 1.0s (Retry 2) 🆕
            M->>Server: Reconnect
            
            alt Final Success
                Server-->>M: Result
                M-->>D: Return result
            else All Failed
                M-->>D: Error (retries exhausted) 🆕
            end
        end
    else Other Error
        Server--xM: Error
        M-->>D: Detailed Error 🆕
    end
    deactivate M
```

## Phase 4: Registry & Caching System

```mermaid
graph TB
    subgraph "mcp_registry.py"
        A[get_tool_schema] --> B{In Cache?}
        B --> |hit 🆕| C[Return Cached]
        B --> |miss 🆕| D[Load from JSON]
        D --> E[Update Cache 🆕]
        E --> F[Return Schema]
        
        G[get_server_for_tool] --> H{In Cache?}
        H --> |hit 🆕| I[Return Cached]
        H --> |miss 🆕| J[Lookup Server]
        J --> K[Update Cache 🆕]
        K --> L[Return Server]
    end
    
    M[tool_schemas.json] -.->|load| D
    M -.->|load| J
    
    N[Cache Stats 🆕<br/>get_registry_stats] -.->|monitor| B
    N -.->|monitor| H
    
    style B fill:#fff4e1
    style E fill:#fff4e1
    style H fill:#fff4e1
    style K fill:#fff4e1
    style N fill:#ffe1f5
```

## Component Architecture

```mermaid
C4Context
    title MCP Servers Architecture - Component View
    
    Person(user, "User", "Sends requests")
    
    System_Boundary(trinity, "AtlasTrinity") {
        Container(behavior, "BehaviorEngine", "Python", "Intent detection<br/>Strategy selection")
        Container(dispatcher, "ToolDispatcher", "Python", "Tool routing<br/>Validation 🆕<br/>Auto-fill 🆕")
        Container(registry, "MCPRegistry", "Python", "Schema storage<br/>Caching 🆕")
        Container(manager, "MCPManager", "Python", "Session mgmt<br/>Resilience 🆕")
        
        ContainerDb(schemas, "Schemas", "JSON", "tool_schemas.json<br/>mcp_catalog.json")
        ContainerDb(config, "Config", "YAML", "behavior_config.yaml<br/>mcp_servers.json")
    }
    
    System_Ext(mcp1, "macos-use", "GUI automation")
    System_Ext(mcp2, "filesystem", "File operations")
    System_Ext(mcp3, "puppeteer", "Browser control")
    System_Ext(mcp4, "memory", "Knowledge graph")
    System_Ext(mcp_more, "13 more servers...", "Various capabilities")
    
    Rel(user, behavior, "Request")
    Rel(behavior, dispatcher, "Route tool")
    Rel(dispatcher, registry, "Get schema (cached 🆕)")
    Rel(dispatcher, manager, "Execute tool")
    Rel(manager, mcp1, "MCP Protocol")
    Rel(manager, mcp2, "MCP Protocol")
    Rel(manager, mcp3, "MCP Protocol")
    Rel(manager, mcp4, "MCP Protocol")
    Rel(manager, mcp_more, "MCP Protocol")
    
    Rel(registry, schemas, "Load")
    Rel(behavior, config, "Load")
    Rel(dispatcher, config, "Load")
    Rel(manager, config, "Load")
```

## Performance Metrics Flow

```mermaid
graph LR
    subgraph "Monitoring 🆕"
        A[Tool Call Start] --> B[Record Start Time]
        B --> C[Execute]
        C --> D[Record End Time]
        D --> E{Duration > 5s?}
        E --> |yes| F[Log Slow Call]
        E --> |no| G[Track Metrics]
        
        H[Cache Access] --> I{Hit or Miss?}
        I --> |hit| J[Increment Hits]
        I --> |miss| K[Increment Misses]
        
        L[Connection Error] --> M[Increment Retries]
        M --> N{Max Retries?}
        N --> |yes| O[Log Exhausted]
        N --> |no| P[Backoff & Retry]
    end
    
    style F fill:#ffe1e1
    style J fill:#e1ffe1
    style K fill:#ffe1e1
    style O fill:#ffe1e1
```

## Data Flow: Example Request

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant B as BehaviorEngine
    participant D as ToolDispatcher
    participant R as MCPRegistry
    participant M as MCPManager
    participant FS as filesystem

    U->>B: "Знайди config.yaml"
    B->>B: Classify: info_query
    B->>D: Route tool
    D->>D: Map "знайди" → "find_file"
    D->>R: get_tool_schema("find_file") 🆕
    
    alt Cache Hit 🆕
        R-->>D: Schema (cached)
    else Cache Miss
        R->>R: Load from JSON
        R->>R: Update cache 🆕
        R-->>D: Schema
    end
    
    D->>D: Validate args
    D->>D: Missing: pattern ❌
    D-->>U: Error: Missing required arg
    
    U->>D: "Знайди config.yaml в поточній папці"
    D->>D: Validate: ✓
    D->>D: Convert types 🆕
    D->>M: Execute(filesystem, find_file, args)
    
    M->>M: Start metrics 🆕
    M->>FS: call_tool(find_file, args)
    FS-->>M: [results]
    M->>M: Track duration: 0.3s 🆕
    M-->>U: Result
```

---

## How to Use This Diagram

### View Locally (VSCode)
1. Install extension: **Markdown Preview Mermaid Support**
2. Open this file
3. Click "Preview" button
4. Diagrams render automatically ✨

### View on GitHub
- Push to GitHub
- Open this file in browser
- Mermaid renders automatically ✨

### Export as Image
```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Convert to PNG/SVG
mmdc -i mcp_architecture_diagram.md -o architecture.png
mmdc -i mcp_architecture_diagram.md -o architecture.svg
```

### Update Process
1. **Code changes** → Update relevant Mermaid diagram
2. **Commit** → Diagrams update automatically
3. **No manual image editing needed!** 🎉

---

## Diagram Legend

| Symbol | Meaning |
|--------|---------|
| 🆕 | New in v4.7 |
| ✓ | Success path |
| ❌ | Error path |
| 📊 | Metrics/monitoring |
| 🔄 | Retry logic |

---

**Last Updated:** 2026-01-26 (v4.7)  
**Auto-updates with:** Code changes in `src/brain/`
