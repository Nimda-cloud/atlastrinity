# Architecture Diagrams - Internal Storage

This folder contains auto-updated architecture diagrams for AtlasTrinity's internal use by agents (Atlas, Tetyana, Grisha).

## Purpose

- **Auto-generated**: Updated via MCP devtools on code changes
- **Agent access**: Agents can read current architecture state
- **Self-healing**: Used for self-diagnosis and problem analysis
- **Always fresh**: Reflects latest git commits/diffs

## Structure

```
architecture_diagrams/
├── README.md                          # This file
├── mcp_architecture.md                # Source Mermaid diagrams
└── exports/                           # Auto-generated images
    ├── mcp_architecture-1.png
    ├── mcp_architecture-2.png
    └── ...
```

## Update Process

**Automatic via MCP:**
```bash
npm run diagram:auto-update
```

**Manual:**
```bash
npm run diagram:export
```

## Files Updated on Code Changes

1. `src/brain/data/architecture_diagrams/mcp_architecture.md` (internal)
2. `.agent/docs/mcp_architecture_diagram.md` (documentation)

Both are kept in sync automatically via `devtools.update_architecture_diagrams` MCP tool.

---

**Last Updated:** Auto-updated via MCP devtools  
**Related MCP Servers:** devtools, git, sequential-thinking
