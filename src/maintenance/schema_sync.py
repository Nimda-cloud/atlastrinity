#!/usr/bin/env python3
import json
from pathlib import Path
from typing import Any


def _json_type_to_str(t: Any) -> str:
    if isinstance(t, list):
        # e.g. ["string", "null"]
        non_null = [x for x in t if x != "null"]
        if len(non_null) == 1:
            return _json_type_to_str(non_null[0])
        return "any"
    if not isinstance(t, str):
        return "any"
    return {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }.get(t, "any")


def _tool_to_schema(server_name: str, tool: dict[str, Any]) -> dict[str, Any]:
    schema = tool.get("inputSchema") or {}
    props: dict[str, Any] = schema.get("properties") or {}
    required: list[str] = list(schema.get("required") or [])

    optional = [k for k in props if k not in required]

    types: dict[str, str] = {}
    for k, v in props.items():
        types[k] = _json_type_to_str(v.get("type"))

    out: dict[str, Any] = {
        "server": server_name,
        "required": required,
        "optional": optional,
        "types": types,
        "description": tool.get("description", ""),
    }
    return out


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent.parent
    live_path = Path("/tmp/mcp_tools_live_full.json")
    if not live_path.exists():
        raise SystemExit(
            "Missing /tmp/mcp_tools_live_full.json. Run scripts/test_all_mcp_runtime.py or the live tools/list dump first."
        )

    live = json.loads(live_path.read_text())

    # Load existing schemas (keep any alias entries that are already present)
    schemas_path = project_root / "src" / "brain" / "data" / "tool_schemas.json"
    existing: dict[str, Any] = json.loads(schemas_path.read_text()) if schemas_path.exists() else {}

    # Build regenerated schemas for all stdio servers
    regenerated: dict[str, Any] = {}
    for server_name, payload in live.items():
        if payload.get("status") != "ok":
            continue
        for tool in payload.get("tools") or []:
            tool_name = tool.get("name")
            if not tool_name:
                continue
            # Some ecosystems expose same tool name on multiple servers (e.g. "screenshot").
            # tool_schemas.json has a single namespace, so keep first-seen ownership.
            if tool_name in regenerated and regenerated[tool_name].get("server") != server_name:
                continue
            regenerated[tool_name] = _tool_to_schema(server_name, tool)

    # Merge: regenerated tool schemas override old non-alias entries
    merged: dict[str, Any] = {}

    # Keep alias entries from existing
    merged = {k: v for k, v in existing.items() if isinstance(v, dict) and "alias_for" in v}

    # Add/override with regenerated
    merged.update(regenerated)

    # Also keep any non-alias entries for internal/native tools not present in live dump
    for k, v in existing.items():
        if k in merged:
            continue
        if isinstance(v, dict) and "alias_for" in v:
            continue
        merged[k] = v

    # Stable order
    ordered = {k: merged[k] for k in sorted(merged.keys())}
    schemas_path.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
