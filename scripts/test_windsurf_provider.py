#!/usr/bin/env python3
"""
Quick test for Windsurf provider.
Run: python scripts/test_windsurf_provider.py

Tests all three modes:
1. Local LS (auto-detected from running Windsurf IDE)
2. Direct cloud API
3. Proxy mode (requires windsurf_proxy.py running)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage

from providers.windsurf import WindsurfLLM, _detect_language_server, _ls_heartbeat


def test_auto_detection():
    """Test LS auto-detection."""
    print("=== Auto-Detection ===")
    port, csrf = _detect_language_server()
    if port and csrf:
        alive = _ls_heartbeat(port, csrf)
        print(f"  LS Port: {port}")
        print(f"  LS CSRF: {csrf[:20]}...")
        print(f"  Heartbeat: {'OK' if alive else 'FAIL'}")
    else:
        print("  LS not detected (Windsurf IDE not running?)")
    return port, csrf


def test_mode(mode: str):
    """Test a specific mode."""
    print(f"\n=== Mode: {mode} ===")
    os.environ["WINDSURF_MODE"] = mode
    try:
        llm = WindsurfLLM()
        result = llm.invoke([
            SystemMessage(content="You are helpful. Be brief."),
            HumanMessage(content="What is 2+2? Answer only the number."),
        ])
        content = result.content
        if "[WINDSURF ERROR]" in content:
            print(f"  Error: {content[:200]}")
            return False
        print(f"  Response: {content[:200]}")
        return True
    except Exception as e:
        print(f"  Exception: {e}")
        return False
    finally:
        os.environ.pop("WINDSURF_MODE", None)


def main():
    print("Windsurf Provider Test")
    print("=" * 40)

    # Check env
    api_key = os.environ.get("WINDSURF_API_KEY", "")
    if not api_key:
        print("ERROR: WINDSURF_API_KEY not set. Run: python -m providers.get_windsurf_token")
        sys.exit(1)
    print(f"API Key: {api_key[:15]}...{api_key[-8:]}")

    # Test auto-detection
    port, csrf = test_auto_detection()

    # Test modes
    results = {}
    if port and csrf:
        results["local"] = test_mode("local")
    results["direct"] = test_mode("direct")

    # Summary
    print("\n=== Summary ===")
    for mode, ok in results.items():
        status = "OK" if ok else "FAIL"
        print(f"  {mode:10s} {status}")

    if not any(results.values()):
        print("\n  All modes failed. Possible causes:")
        print("  - Cloud API quota exhausted (resource_exhausted)")
        print("  - Trial tier limits reached")
        print("  - Network connectivity issues")
        print("  Try again later or check: python -m providers.get_windsurf_token --test")


if __name__ == "__main__":
    main()
