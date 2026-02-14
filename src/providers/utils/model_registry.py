"""
Model Registry
==============

Single source of truth for loading model definitions from config/all_models.json.
All providers and proxies should use this module instead of hardcoding model lists.

Usage:
    from providers.utils.model_registry import get_copilot_models, get_windsurf_models
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

# ─── Windsurf Internal UID Map ────────────────────────────────────────────────
# Display name → Windsurf/Codeium internal proto model UID
# This is the ONLY place where Windsurf internal UIDs should be defined.
WINDSURF_UID_MAP: dict[str, str] = {
    "swe-1.5": "MODEL_SWE_1_5",
    "deepseek-r1": "MODEL_DEEPSEEK_R1",
    "swe-1": "MODEL_SWE_1",
    "grok-code-fast-1": "MODEL_GROK_CODE_FAST_1",
    "kimi-k2.5": "kimi-k2-5",
    "windsurf-fast": "MODEL_CHAT_11121",
}

# ─── Config Path Resolution ──────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ALL_MODELS_PATH = _PROJECT_ROOT / "config" / "all_models.json"


def _find_all_models_path() -> Path:
    """Resolve the path to all_models.json."""
    # 1. Relative to project root
    if _ALL_MODELS_PATH.exists():
        return _ALL_MODELS_PATH
    # 2. Environment variable override
    env_path = os.getenv("ALL_MODELS_JSON")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    # 3. Fallback — return default even if missing (will raise on load)
    return _ALL_MODELS_PATH


# ─── Loaders ─────────────────────────────────────────────────────────────────


def load_all_models() -> list[dict[str, Any]]:
    """Load all model definitions from config/all_models.json.

    Returns:
        List of model dicts (each with 'id', 'vendor', 'capabilities', etc.)
    """
    path = _find_all_models_path()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("data", [])


def get_copilot_models() -> dict[str, str]:
    """Get Copilot model display names as {id: id}.

    Filters all_models.json entries where vendor == 'Copilot'.
    """
    models = load_all_models()
    return {m["id"]: m["id"] for m in models if m.get("vendor") == "Copilot"}


def get_windsurf_models() -> dict[str, str]:
    """Get Windsurf model display names mapped to internal UIDs.

    Filters all_models.json entries where vendor == 'Windsurf',
    then maps each to its Windsurf internal proto UID via WINDSURF_UID_MAP.

    Models not found in WINDSURF_UID_MAP use their display name as fallback.
    """
    models = load_all_models()
    result: dict[str, str] = {}
    for m in models:
        if m.get("vendor") == "Windsurf":
            model_id: str = m["id"]
            uid = WINDSURF_UID_MAP.get(model_id, model_id)
            if uid is not None:
                result[model_id] = uid
    return result
