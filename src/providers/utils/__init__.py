"""
Provider Utilities
==================

Configuration management, token utilities, and provider switching tools.
"""

from .switch_provider import (
    get_current_provider,
    show_status,
    switch_to_copilot,
    switch_to_windsurf,
)
from .switch_provider import main as switch_provider_main

# Token utilities (import main functions for CLI access)
try:
    from .get_copilot_token import main as copilot_token_main
    from .get_windsurf_token import main as windsurf_token_main
except ImportError:
    copilot_token_main = None  # type: ignore
    windsurf_token_main = None  # type: ignore

__all__ = [
    "copilot_token_main",
    "get_current_provider",
    "show_status",
    "switch_provider_main",
    "switch_to_copilot",
    "switch_to_windsurf",
    "windsurf_token_main",
]
