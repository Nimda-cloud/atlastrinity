"""Compatibility Shim for brain.server
Redirects to the new modular location: src.brain.core.server.server
"""

import os
import sys

# Ensure src is in PYTHONPATH if not already
SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(SRC_ROOT, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

if __name__ == "__main__":
    from src.brain.core.server.server import main  # pyre-ignore

    main()
else:
    from src.brain.core.server.server import *  # noqa: F403 # pyre-ignore
