"""Compatibility Shim for brain.server
Redirects to the new modular location: src.brain.core.server.server
"""

import os
import sys

# Ensure src is in PYTHONPATH if not already
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if os.path.join(PROJECT_ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

if __name__ == "__main__":
    from src.brain.core.server.server import main

    main()
else:
    from src.brain.core.server.server import *  # noqa: F403
