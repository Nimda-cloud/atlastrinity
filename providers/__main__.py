#!/usr/bin/env python3
"""
Provider CLI
============

Command-line interface for managing LLM providers.

Usage:
    python -m providers switch windsurf
    python -m providers switch copilot
    python -m providers status
    python -m providers test
    python -m providers quick-test
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Provider CLI - AtlasTrinity")
        print("=" * 40)
        print("Usage:")
        print("  python -m providers switch <windsurf|copilot>")
        print("  python -m providers status")
        print("  python -m providers test")
        print("  python -m providers quick-test")
        print("  python -m providers token <copilot|windsurf> [args...]")
        print()
        print("Examples:")
        print("  python -m providers switch windsurf")
        print("  python -m providers status")
        print("  python -m providers token windsurf --test")
        print("  python -m providers token copilot --method vscode")
        return

    command = sys.argv[1].lower()

    if command == "switch":
        if len(sys.argv) < 3:
            print("Error: Missing provider name")
            print("Usage: python -m providers switch <windsurf|copilot>")
            return

        provider = sys.argv[2].lower()
        if provider not in ["windsurf", "copilot"]:
            print("Error: Provider must be 'windsurf' or 'copilot'")
            return

        # Import and run switch utility
        try:
            from providers.utils.switch_provider import main as switch_provider_main

            sys.argv = ["switch_provider.py", provider]
            switch_provider_main()
        except ImportError:
            print("Error: Could not import switch_provider utility")
            return

    elif command == "status":
        try:
            from providers.utils.switch_provider import show_status

            show_status()
        except ImportError:
            print("Error: Could not import status utility")
            return

    elif command == "test":
        try:
            from providers.tests.test_windsurf_config import test_config_integration

            test_config_integration()
        except ImportError:
            print("Error: Could not import test utility")
            return

    elif command == "quick-test":
        try:
            from providers.tests.quick_windsurf_test import quick_test

            quick_test()
        except ImportError:
            print("Error: Could not import quick test utility")
            return

    elif command == "token":
        if len(sys.argv) < 3:
            print("Error: Missing token provider")
            print("Usage: python -m providers token <copilot|windsurf> [args...]")
            return

        token_provider = sys.argv[2].lower()
        args = sys.argv[3:]  # Pass remaining args to token utility

        if token_provider == "windsurf":
            try:
                from providers.utils.get_windsurf_token import main as windsurf_token_main

                sys.argv = ["get_windsurf_token.py", *args]
                windsurf_token_main()
            except ImportError:
                print("Error: Could not import windsurf token utility")
                return
        elif token_provider == "copilot":
            try:
                from providers.utils.get_copilot_token import main as copilot_token_main

                sys.argv = ["get_copilot_token.py", *args]
                copilot_token_main()
            except ImportError:
                print("Error: Could not import copilot token utility")
                return
        else:
            print("Error: Token provider must be 'copilot' or 'windsurf'")

    else:
        print(f"Unknown command: {command}")
        print("Available commands: switch, status, test, quick-test, token")


if __name__ == "__main__":
    main()
