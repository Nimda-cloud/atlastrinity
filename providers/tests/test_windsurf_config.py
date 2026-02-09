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
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

from providers.factory import create_llm, get_provider_name  # noqa: E402
from src.brain.config_loader import config  # noqa: E402


def test_config_integration():
    """Test Windsurf integration with system configuration."""
    print("=" * 60)
    print("WINDSURF CONFIGURATION INTEGRATION TEST")
    print("=" * 60)

    # Get current provider
    provider = get_provider_name()
    print(f"\nCurrent provider: {provider}")

    # Test with configuration override
    print("\n--- Testing with Windsurf provider ---")

    # Override to windsurf for testing
    os.environ["LLM_PROVIDER"] = "windsurf"

    # Create LLM using factory (reads from config)
    llm = create_llm(model_name="deepseek-v3")
    print(f"Created LLM: {type(llm).__name__}")
    print(f"Model: {getattr(llm, 'model_name', 'N/A')}")

    # Test basic invocation
    try:
        messages = [
            SystemMessage(content="Answer briefly and concisely."),
            HumanMessage(content="What is the capital of Ukraine? One word only."),
        ]

        t0 = time.time()
        result = llm.invoke(messages)
        elapsed = time.time() - t0

        content = result.content[:200] if result.content else "<empty>"
        success = content and "ERROR" not in content and len(content) > 1

        print(f"Response ({elapsed:.1f}s): {content}")
        print(f"Status: {'✅ PASS' if success else '❌ FAIL'}")

    except Exception as e:
        print(f"❌ FAIL: {e}")

    return provider


def test_model_selection():
    """Test different model configurations."""
    print("\n" + "=" * 60)
    print("MODEL SELECTION TEST")
    print("=" * 60)

    # Test models from config
    models_to_test = [
        ("deepseek-v3", "Free model - general purpose"),
        ("deepseek-r1", "Free model - reasoning"),
        ("swe-1", "Free model - coding"),
    ]

    os.environ["LLM_PROVIDER"] = "windsurf"

    for model_name, description in models_to_test:
        print(f"\n--- Testing {model_name} ---")
        print(f"Description: {description}")

        try:
            llm = create_llm(model_name=model_name)

            # Simple test
            messages = [
                SystemMessage(content="Answer in one sentence."),
                HumanMessage(content="What is 2+2?"),
            ]

            t0 = time.time()
            result = llm.invoke(messages)
            elapsed = time.time() - t0

            content = result.content[:100] if result.content else "<empty>"
            success = content and "ERROR" not in content

            print(f"  Response ({elapsed:.1f}s): {content}")
            print(f"  Status: {'✅ PASS' if success else '❌ FAIL'}")

        except Exception as e:
            print(f"  ❌ FAIL: {e}")


def show_config_info():
    """Show current configuration information."""
    print("\n" + "=" * 60)
    print("CONFIGURATION INFORMATION")
    print("=" * 60)

    print(f"\nConfig location: {Path.home()}/.config/atlastrinity/config.yaml")
    print(f"Current provider: {config.get('models.provider')}")
    print(f"Default model: {config.get('models.default')}")
    print(f"Reasoning model: {config.get('models.reasoning')}")

    print("\nTo switch to Windsurf provider:")
    print("1. Edit ~/.config/atlastrinity/config.yaml:")
    print("   models:")
    print("     provider: 'windsurf'")
    print("     default: 'deepseek-v3'")
    print("     reasoning: 'deepseek-r1'")
    print("\n2. Or use environment variable:")
    print("   export LLM_PROVIDER=windsurf")
    print("\n3. Or override in code:")
    print("   llm = create_llm(model_name='deepseek-v3', provider='windsurf')")


def test_agent_integration():
    """Test Windsurf with agent configuration."""
    print("\n" + "=" * 60)
    print("AGENT INTEGRATION TEST")
    print("=" * 60)

    # Test Atlas agent with windsurf
    os.environ["LLM_PROVIDER"] = "windsurf"

    try:
        from src.brain.agents.atlas import Atlas

        # Create agent (will use windsurf provider)
        atlas = Atlas()
        print("Atlas agent created successfully")
        print(f"Agent model: {getattr(atlas, 'model', 'N/A')}")
        print(f"Deep model: {getattr(atlas, 'deep_model', 'N/A')}")

        # Test simple interaction
        response = atlas.chat("What is Python? One sentence.")
        if hasattr(response, "__await__"):
            # Handle coroutine
            import asyncio

            response = asyncio.run(response)  # type: ignore
        print(f"Atlas response: {response[:100]}...")  # type: ignore

    except Exception as e:
        print(f"❌ Agent test failed: {e}")


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

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
