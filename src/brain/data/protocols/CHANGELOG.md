# Protocols Changelog

## 2026-01-26 - Protocol Consolidation & Updates

### Moved
- All agent protocols consolidated in `src/brain/data/protocols/`
- Separated from Windsurf workflows (`.agent/workflows/`)

### Fixed
- **data_protocol.txt**: Removed Bengali text, updated paths to use `~/.config/atlastrinity/workspace`
- **storage_protocol.txt**: Removed reference to non-existent `bulk_ingest_table`, updated to use `ingest_verified_dataset`
- **self-healing-protocol.md**: Fixed diagram paths (removed `~/.config/atlastrinity` prefix, use relative paths)
- **system_mastery_protocol.txt**: Updated documentation hierarchy with correct paths
- **vibe_docs.txt**: Added integration section (Architecture Diagrams, GitHub MCP, devtools MCP)

### Updated
- **create-new-program.md**: Status changed to ACTIVE, protocol is integrated
- **self-healing-protocol.md**: Status changed to ACTIVE, protocol is integrated

### Current Protocol Status

| Protocol | Status | Integration | Last Updated |
|----------|--------|-------------|--------------|
| create-new-program.md | ✅ ACTIVE | behavior_config v4.8.0 | 2026-01-26 |
| self-healing-protocol.md | ✅ ACTIVE | behavior_config v4.8.0 | 2026-01-26 |
| vibe_docs.txt | ✅ ACTIVE | Always active | 2026-01-26 |
| data_protocol.txt | ✅ ACTIVE | Always active | 2026-01-26 |
| search_protocol.txt | ✅ ACTIVE | Always active | 2026-01-26 |
| storage_protocol.txt | ✅ ACTIVE | Always active | 2026-01-26 |
| sdlc_protocol.txt | ✅ ACTIVE | Always active | 2026-01-26 |
| task_protocol.txt | ✅ ACTIVE | Always active | 2026-01-26 |
| system_mastery_protocol.txt | ✅ ACTIVE | Always active | 2026-01-26 |
| voice_protocol.txt | ✅ ACTIVE | Always active | 2026-01-26 |

### Configuration References

All protocols are referenced in:
- `config/behavior_config.yaml.template` (header + specific sections)
- Read by: Atlas, Tetyana, Grisha, Vibe (internal agents)

### Tools Referenced

**Verified to exist in tool_schemas.json:**
- ✅ vibe_prompt, vibe_analyze_error, vibe_code_review, vibe_implement_feature
- ✅ ingest_verified_dataset, trace_data_chain
- ✅ devtools_update_architecture_diagrams
- ❌ bulk_ingest_table (removed from protocol - does not exist)

### Paths Corrected

**Old (incorrect):**
- `~/.config/atlastrinity/.agent/docs/...`
- `workspace/workspace` (double)
- `bulk_ingest_table` tool reference

**New (correct):**
- `.agent/docs/...` (relative to PROJECT_ROOT)
- `~/.config/atlastrinity/workspace`
- `ingest_verified_dataset` tool

---

## Protocol Maintenance Guidelines

1. **Before updating**: Verify tool exists in `src/brain/data/tool_schemas.json`
2. **Paths**: Use relative paths for internal files, `~/.config/atlastrinity/` for global config
3. **Status**: Mark as ACTIVE only when integrated in behavior_config
4. **Testing**: Verify protocol works in real agent execution
5. **Documentation**: Update this CHANGELOG when making changes
