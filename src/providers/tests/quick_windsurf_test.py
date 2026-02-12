#!/usr/bin/env python3
"""
Quick Windsurf Test with Configuration
======================================

Simple test script to verify Windsurf provider works with system configuration.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main():
    print("=" * 50)
    print("QUICK WINDSURF CONFIGURATION TEST")
    print("=" * 50)

    # Test 1: Factory with windsurf override
    print("\n1. Testing factory with windsurf provider...")

    from langchain_core.messages import HumanMessage, SystemMessage

    from src.providers.factory import create_llm

    try:
        # Create LLM with windsurf provider
        llm = create_llm(model_name="deepseek-v3", provider="windsurf")
        print(f"   ✅ Created: {type(llm).__name__}")

        # Test simple invocation
        messages = [
            SystemMessage(content="Answer in one word."),
            HumanMessage(content="What is 2+2?"),
        ]

        result = llm.invoke(messages)
        content = result.content[:50] if result.content else "<empty>"

        if "ERROR" not in content and len(content) > 0:
            print(f"   ✅ Response: {content}")
        else:
            print(f"   ❌ Failed: {content}")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    # Test 2: Show configuration info
    print("\n2. Configuration information...")

    from src.brain.config_loader import config

    print("   Config location: ~/.config/atlastrinity/config.yaml")
    print(f"   Current provider: {config.get('models.provider')}")
    print(f"   Default model: {config.get('models.default')}")

    print("\n3. How to enable Windsurf globally:")
    print("   Edit ~/.config/atlastrinity/config.yaml:")
    print("   models:")
    print("     provider: 'windsurf'")
    print("     default: 'deepseek-v3'")
    print("     reasoning: 'deepseek-r1'")

    print("\n   Or use environment variable:")
    print("   export LLM_PROVIDER=windsurf")

    print("\n4. Available Windsurf models:")
    print("   Free: deepseek-v3, deepseek-r1, swe-1, grok-code-fast-1, kimi-k2.5")
    print("   Premium: claude-4-sonnet, claude-4.5-opus, gpt-4.1, gpt-5.1, swe-1.5")

    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)


# Alias for compatibility with imports
quick_test = main

if __name__ == "__main__":
    main()
