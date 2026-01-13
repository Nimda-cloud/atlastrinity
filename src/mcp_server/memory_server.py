import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import FastMCP

server = FastMCP("memory")


def _store_path() -> Path:
    return Path.home() / ".config" / "atlastrinity" / "memory_store.json"


def _load_store() -> Dict[str, Any]:
    p = _store_path()
    if not p.exists():
        return {"entities": {}}
    try:
        return json.loads(p.read_text(encoding="utf-8")) or {"entities": {}}
    except Exception:
        return {"entities": {}}


def _save_store(store: Dict[str, Any]) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_entity(ent: Dict[str, Any]) -> Dict[str, Any]:
    name = str(ent.get("name", "")).strip()
    entity_type = str(ent.get("entityType", "concept")).strip() or "concept"
    observations = ent.get("observations") or []
    if not isinstance(observations, list):
        observations = [str(observations)]
    observations = [str(o) for o in observations if str(o).strip()]
    return {"name": name, "entityType": entity_type, "observations": observations}


@server.tool()
def create_entities(entities: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(entities, list) or not entities:
        return {"error": "entities must be a non-empty list"}

    store = _load_store()
    db = store.setdefault("entities", {})

    created: List[str] = []
    updated: List[str] = []

    for ent in entities:
        n = _normalize_entity(ent)
        name = n["name"]
        if not name:
            continue

        if name in db:
            # merge observations
            cur = db[name]
            cur_obs = cur.get("observations") or []
            if not isinstance(cur_obs, list):
                cur_obs = []
            merged = list(dict.fromkeys([*cur_obs, *n["observations"]]))
            cur["entityType"] = cur.get("entityType") or n["entityType"]
            cur["observations"] = merged
            updated.append(name)
        else:
            db[name] = {
                "entityType": n["entityType"],
                "observations": n["observations"],
            }
            created.append(name)

    _save_store(store)
    return {"success": True, "created": created, "updated": updated}


@server.tool()
def add_observations(name: str, observations: List[str]) -> Dict[str, Any]:
    name = str(name or "").strip()
    if not name:
        return {"error": "name is required"}
    if not isinstance(observations, list) or not observations:
        return {"error": "observations must be a non-empty list"}

    store = _load_store()
    db = store.setdefault("entities", {})

    ent = db.get(name) or {"entityType": "concept", "observations": []}
    cur_obs = ent.get("observations") or []
    if not isinstance(cur_obs, list):
        cur_obs = []

    new_obs = [str(o) for o in observations if str(o).strip()]
    ent["observations"] = list(dict.fromkeys([*cur_obs, *new_obs]))
    db[name] = ent

    _save_store(store)
    return {"success": True, "name": name, "observations": ent["observations"]}


@server.tool()
def get_entity(name: str) -> Dict[str, Any]:
    name = str(name or "").strip()
    if not name:
        return {"error": "name is required"}

    store = _load_store()
    db = store.get("entities", {}) or {}
    ent = db.get(name)
    if not ent:
        return {"error": "not found"}
    return {"success": True, "name": name, **ent}


@server.tool()
def list_entities() -> Dict[str, Any]:
    store = _load_store()
    db = store.get("entities", {}) or {}
    names = sorted(db.keys())
    return {"success": True, "names": names, "count": len(names)}


@server.tool()
def search(query: str, limit: int = 10) -> Dict[str, Any]:
    q = str(query or "").strip().lower()
    if not q:
        return {"error": "query is required"}

    lim = max(1, min(int(limit), 50))
    store = _load_store()
    db = store.get("entities", {}) or {}

    matches: List[Dict[str, Any]] = []
    for name, ent in db.items():
        text = " ".join(
            [
                name,
                ent.get("entityType", ""),
                *[str(o) for o in (ent.get("observations") or [])],
            ]
        )
        if q in text.lower():
            matches.append(
                {
                    "name": name,
                    "entityType": ent.get("entityType"),
                    "observations": ent.get("observations") or [],
                }
            )
            if len(matches) >= lim:
                break

    return {"success": True, "results": matches, "count": len(matches)}


@server.tool()
def search_nodes(query: str, limit: int = 10) -> Dict[str, Any]:
    """Alias for search function to maintain compatibility"""
    return search(query, limit)


@server.tool()
def delete_entity(name: str) -> Dict[str, Any]:
    name = str(name or "").strip()
    if not name:
        return {"error": "name is required"}

    store = _load_store()
    db = store.get("entities", {}) or {}
    if name not in db:
        return {"success": True, "deleted": False}

    del db[name]
    store["entities"] = db
    _save_store(store)
    return {"success": True, "deleted": True}


if __name__ == "__main__":
    server.run()
