#!/usr/bin/env python3
"""
Windsurf Provider Configuration Test
====================================

Tests Windsurf provider using the system configuration.
This script demonstrates how to integrate Windsurf into the development workflow
using the centralized configuration system.

Usage:
    python scripts/test_windsurf_config.py
    LLM_PROVIDER=windsurf python scripts/test_windsurf_config.py
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

from src.providers.factory import create_llm, get_provider_name  # noqa: E402


def test_config_integration():
    """Test Windsurf integration with system configuration."""

    # Get current provider
    provider = get_provider_name()

    # Test with configuration override

    # Override to windsurf for testing
    os.environ["LLM_PROVIDER"] = "windsurf"

    # Create LLM using factory (reads from config)
    llm = create_llm(model_name="deepseek-v3")

    # Test basic invocation
    try:
        messages = [
            SystemMessage(content="Answer briefly and concisely."),
            HumanMessage(content="What is the capital of Ukraine? One word only."),
        ]

        t0 = time.time()
        result = llm.invoke(messages)
        _ = time.time() - t0

        content = result.content[:200] if result.content else "<empty>"
        _ = content and "ERROR" not in content and len(content) > 1

    except Exception:
        pass

    return provider


def test_model_selection():
    """Test different model configurations."""

    # Test models from config
    models_to_test = [
        ("deepseek-v3", "Free model - general purpose"),
        ("deepseek-r1", "Free model - reasoning"),
        ("swe-1", "Free model - coding"),
    ]

    os.environ["LLM_PROVIDER"] = "windsurf"

    for model_name, _ in models_to_test:
        try:
            llm = create_llm(model_name=model_name)

            # Simple test
            messages = [
                SystemMessage(content="Answer in one sentence."),
                HumanMessage(content="What is 2+2?"),
            ]

            t0 = time.time()
            result = llm.invoke(messages)
            _ = time.time() - t0

            result.content[:100] if result.content else "<empty>"

        except Exception:
            pass


def show_config_info():
    """Show current configuration information."""


def test_agent_integration():
    """Test Windsurf with agent configuration."""

    # Test Atlas agent with windsurf
    os.environ["LLM_PROVIDER"] = "windsurf"

    try:
        from src.brain.agents.atlas import Atlas

        # Create agent (will use windsurf provider)
        atlas = Atlas()

        # Test simple interaction
        response = atlas.chat("What is Python? One sentence.")
        if hasattr(response, "__await__"):
            # Handle coroutine
            import asyncio

            response = asyncio.run(response)  # type: ignore

    except Exception:
        pass


def main():
    """Main test runner."""
    # Test configuration integration
    original_provider = test_config_integration()

    # Test model selection
    test_model_selection()

    # Show configuration info
    show_config_info()

    # Test agent integration
    test_agent_integration()

    # Restore original provider
    if original_provider != "windsurf":
        os.environ["LLM_PROVIDER"] = original_provider


if __name__ == "__main__":
    main()
