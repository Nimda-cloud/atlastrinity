"""Check that required environment secrets are available in CI."""

import os
import sys


def check_secrets() -> bool:
    """Check for required and optional secrets."""
    # Critical secrets - must be present
    critical_secrets = {
        "GITHUB_TOKEN": "GitHub API access (auto-provided by Actions)",
    }

    # Important secrets - warn if missing
    important_secrets = {
        "OPENAI_API_KEY": "OpenAI models",
        "ANTHROPIC_API_KEY": "Claude models",
        "COPILOT_API_KEY": "GitHub Copilot integration",
    }

    # Optional secrets
    optional_secrets = {
        "SLACK_BOT_TOKEN": "Slack notifications",
        "SLACK_TEAM_ID": "Slack team identification",
    }

    missing_critical = []
    missing_important = []

    # Check critical secrets
    for secret, description in critical_secrets.items():
        if not os.getenv(secret):
            missing_critical.append(f"{secret} ({description})")
        else:
            pass

    # Check important secrets
    for secret, description in important_secrets.items():
        if not os.getenv(secret):
            missing_important.append(f"{secret} ({description})")
        else:
            pass

    # Check optional secrets (info only)
    for secret, description in optional_secrets.items():
        if os.getenv(secret):
            pass
        else:
            pass

    # Report results
    if missing_critical:
        for secret in missing_critical:
            pass
        return False

    if missing_important:
        for secret in missing_important:
            pass

    return True


def main():
    """Main entry point."""
    success = check_secrets()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
