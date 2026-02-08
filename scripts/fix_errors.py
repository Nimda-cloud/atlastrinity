"""
Fix critical errors found in logs
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = str(Path(__file__).parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ["CONFIG_ROOT"] = os.path.expanduser("~/.config/atlastrinity")


def fix_tool_routing():
    """Fix tool routing issues"""
    print("🔧 Fixing tool routing issues...")

    # Check tool_dispatcher.py for correct mappings
    HOME = os.path.expanduser("~")
    PROJECT_ROOT = os.path.join(HOME, "Documents/GitHub/atlastrinity")
    dispatcher_file = os.path.join(PROJECT_ROOT, "src/brain/tool_dispatcher.py")
    if os.path.exists(dispatcher_file):
        with open(dispatcher_file) as f:
            content = f.read()

        # Check if get_clipboard is properly mapped
        if '"get_clipboard": "macos-use_get_clipboard"' in content:
            print("✅ get_clipboard mapping found")
        else:
            print("❌ get_clipboard mapping missing")

        # Check if take_screenshot is properly mapped
        if '"take_screenshot": "macos-use_take_screenshot"' in content:
            print("✅ take_screenshot mapping found")
        else:
            print("❌ take_screenshot mapping missing")

        # Check for analyze_screen mapping
        if '"analyze_screen": "macos-use_analyze_screen"' in content:
            print("✅ analyze_screen mapping found")
        else:
            print("⚠️ analyze_screen mapping may be missing")


def fix_vibe_check_db():
    """Fix vibe_check_db SQL errors"""
    print("🔧 Checking vibe_check_db SQL issues...")

    HOME = os.path.expanduser("~")
    PROJECT_ROOT = os.path.join(HOME, "Documents/GitHub/atlastrinity")
    CONFIG_DIR = os.path.join(HOME, ".config/atlastrinity")

    # Find database file
    db_paths = [
        os.path.join(CONFIG_DIR, "atlastrinity.db"),
        os.path.join(CONFIG_DIR, "database.db"),
        os.path.join(PROJECT_ROOT, "data/atlastrinity.db"),
    ]

    db_file = None
    for path in db_paths:
        if os.path.exists(path):
            db_file = path
            break

    if not db_file:
        print("❌ Database file not found")
        return

    print(f"✅ Database found: {db_file}")

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        # Check table structure
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"✅ Tables found: {[t[0] for t in tables]}")

        # Check tool_executions table structure
        if ("tool_executions",) in tables:
            cursor.execute("PRAGMA table_info(tool_executions);")
            columns = cursor.fetchall()
            print(f"✅ tool_executions columns: {[c[1] for c in columns]}")

        # Check logs table structure
        if ("logs",) in tables:
            cursor.execute("PRAGMA table_info(logs);")
            columns = cursor.fetchall()
            print(f"✅ logs columns: {[c[1] for c in columns]}")

        conn.close()

    except Exception as e:
        print(f"❌ Database error: {e}")


def fix_macos_use_tools():
    """Fix macos-use tool availability"""
    print("🔧 Checking macos-use server...")

    # Check if binary exists
    HOME = os.path.expanduser("~")
    PROJECT_ROOT = os.path.join(HOME, "Documents/GitHub/atlastrinity")
    binary_path = os.path.join(PROJECT_ROOT, "vendor/mcp-server-macos-use/mcp-server-macos-use")
    if os.path.exists(binary_path):
        print("✅ macos-use binary exists")

        # Try to list available tools
        try:
            result = subprocess.run(
                [binary_path, "--help"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                print("✅ macos-use responds to help")
            else:
                print(f"⚠️ macos-use help failed: {result.stderr}")
        except Exception as e:
            print(f"❌ macos-use check failed: {e}")
    else:
        print("❌ macos-use binary not found")
        print("🔨 Building macos-use...")

        build_script = os.path.join(PROJECT_ROOT, "vendor/mcp-server-macos-use/build.sh")
        if os.path.exists(build_script):
            try:
                result = subprocess.run(
                    ["bash", build_script], capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    print("✅ macos-use built successfully")
                else:
                    print(f"❌ Build failed: {result.stderr}")
            except Exception as e:
                print(f"❌ Build error: {e}")


def check_grisha_verification():
    """Check Grisha verification patterns"""
    print("🔧 Checking Grisha verification issues...")

    # Look for verification failures in logs
    brain_log = os.path.expanduser("~/.config/atlastrinity/logs/brain.log")
    if os.path.exists(brain_log):
        with open(brain_log) as f:
            lines = f.readlines()

        verification_failures = 0
        tool_errors = 0

        for line in lines[-1000:]:  # Check last 1000 lines
            if "Grisha rejected:" in line:
                verification_failures += 1
            if "Method not found" in line or "No routing found" in line:
                tool_errors += 1

        print(f"⚠️ Recent verification failures: {verification_failures}")
        print(f"⚠️ Recent tool errors: {tool_errors}")

        if verification_failures > 5:
            print("🔧 High verification failure rate detected")
        if tool_errors > 10:
            print("🔧 High tool error rate detected")


def main():
    """Run all fixes"""
    print("🔧 AtlasTrinity Error Fix Script")
    print("=" * 40)

    fixes = [
        ("Tool Routing", fix_tool_routing),
        ("Database Issues", fix_vibe_check_db),
        ("macOS Tools", fix_macos_use_tools),
        ("Grisha Verification", check_grisha_verification),
    ]

    for name, fix_func in fixes:
        print(f"\n🔄 {name}...")
        try:
            fix_func()
        except Exception as e:
            print(f"❌ {name} failed: {e}")

    print("\n🎉 Error fix analysis completed!")
    print("💡 Review the output above for specific issues to fix manually")


if __name__ == "__main__":
    main()
