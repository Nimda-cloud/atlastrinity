"""
Provider Test Utilities
=======================

Test utilities for provider functionality.
"""

import sys
from pathlib import Path

# Add tests directory to sys.path for direct imports
tests_dir = Path(__file__).parent
if str(tests_dir) not in sys.path:
    sys.path.insert(0, str(tests_dir))

from quick_windsurf_test import quick_test  # noqa: E402
from test_windsurf_config import test_config_integration  # noqa: E402

__all__ = [
    "quick_test",
    "test_config_integration",
]
