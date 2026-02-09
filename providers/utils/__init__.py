"""
Provider Utilities
==================

Configuration management, token utilities, and provider switching tools.
"""

import sys
from pathlib import Path

# Add utils directory to sys.path for direct imports
utils_dir = Path(__file__).parent
if str(utils_dir) not in sys.path:
    sys.path.insert(0, str(utils_dir))

from switch_provider import (  # noqa: E402
    get_current_provider,
    show_status,
    switch_to_copilot,
    switch_to_windsurf,
)
from switch_provider import main as switch_provider_main  # noqa: E402

# Token utilities (import main functions for CLI access)
try:
    from get_copilot_token import main as copilot_token_main  # noqa: E402
    from get_windsurf_token import main as windsurf_token_main  # noqa: E402
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
