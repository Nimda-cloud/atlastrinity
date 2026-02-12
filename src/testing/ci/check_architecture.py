import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent.parent))

from src.mcp_server.devtools_server import devtools_update_architecture_diagrams


def check_architecture():

    # We run the update in "Internal" mode.
    # The function returns a dict with 'updates_made' boolean.
    # We'll use a dry-run approach if possible, but the current tool implementation
    # performs writes.
    # For CI check, we can check if it *would* make changes, or let it make changes
    # and check if any file contents actually changed (git status).

    # Run the update
    # Note: We pass init_git=False because CI envs usually have git but wrapped weirdly,
    # and we definitely don't want to re-init.
    try:
        result = devtools_update_architecture_diagrams(
            project_path=None,  # Internal mode
            commits_back=1,
            init_git=False,
            use_reasoning=False,
        )

        if result.get("error"):
            sys.exit(1)

        if result.get("updates_made"):
            updates = result.get("files_updated", [])
            for f in updates:
                pass

            # If we are in strict mode, exit 1.
            # However, the tool *already wrote* the files.
            # So looking at git status is actually the best way.
            # But wait, devtools_update_architecture_diagrams changes the file content
            # with a timestamp 'AUTO-UPDATED: ...'.
            # This means it ALWAYS updates the file if it runs, even if structure is same?
            # Let's check logic:
            # "if not response['analysis']['has_changes']: return ... updates_made=False"
            # So if code didn't change, it returns False.
            # If code changed, it returns True.

            # So if updates_made is True, it means code changes triggered a diagram update.
            # This implies the committed diagram is old.
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    check_architecture()
