"""
Provider Module
===============

Centralized module for all LLM provider functionality including:
- Provider implementations (Copilot, Windsurf)
- Token management utilities
- Configuration management
- Testing utilities
- Provider switching tools

Structure:
├── providers/
│   ├── __init__.py          # Main module exports
│   ├── __main__.py          # CLI interface
│   ├── factory.py           # Provider factory
│   ├── copilot.py           # Copilot provider
│   ├── windsurf.py          # Windsurf provider
│   ├── utils/               # All utilities
│   │   ├── __init__.py
│   │   ├── switch_provider.py    # Provider switching
│   │   ├── get_copilot_token.py  # Copilot token utility
│   │   └── get_windsurf_token.py # Windsurf token utility
│   └── tests/               # Test utilities
│       ├── __init__.py
│       ├── test_windsurf_config.py
│       └── quick_windsurf_test.py

Usage:
    from providers import create_llm
    from providers.windsurf import WindsurfLLM
    from providers.copilot import CopilotLLM
    from providers.utils import switch_to_windsurf
    from providers.tests import quick_test
"""

import sys
from pathlib import Path

# Add providers directory to sys.path for submodule imports
providers_dir = Path(__file__).parent
if str(providers_dir) not in sys.path:
    sys.path.insert(0, str(providers_dir))

from .copilot import CopilotLLM  # noqa: E402
from .factory import create_llm, get_provider_name  # noqa: E402
from .windsurf import WindsurfLLM  # noqa: E402

# Import utilities from submodules
try:
    from .tests import quick_test, test_config_integration  # noqa: E402
    from .utils import (  # noqa: E402
        copilot_token_main,
        show_status,
        switch_to_copilot,
        switch_to_windsurf,
        windsurf_token_main,
    )
except ImportError:
    # These are optional utilities that may not be needed in all contexts
    switch_to_windsurf = None  # type: ignore
    switch_to_copilot = None  # type: ignore
    show_status = None  # type: ignore
    copilot_token_main = None  # type: ignore
    windsurf_token_main = None  # type: ignore
    test_config_integration = None  # type: ignore
    quick_test = None  # type: ignore

__all__ = [
    "CopilotLLM",
    "WindsurfLLM",
    "copilot_token_main",
    "create_llm",
    "get_provider_name",
    "quick_test",
    "show_status",
    "switch_to_copilot",
    "switch_to_windsurf",
    "test_config_integration",
    "windsurf_token_main",
]

# Version info
__version__ = "1.0.0"
__author__ = "AtlasTrinity Team"
