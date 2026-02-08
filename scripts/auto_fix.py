"""
Auto-fix script for common AtlasTrinity issues
"""

import os
from datetime import datetime


def fix_vibe_rate_limit():
    """Fix Vibe rate limiting issues"""
    print("🔧 Fixing Vibe rate limiting...")

    vibe_config = os.path.expanduser("~/.config/atlastrinity/vibe_config.yaml")
    if not os.path.exists(vibe_config):
        print("⚠️ Vibe config not found, creating default...")
        default_config = {
            "rate_limit": {"requests_per_minute": 60, "burst_size": 10, "retry_delay": 10},
            "timeout": {"default": 60, "long_running": 3600},
        }

        import yaml

        with open(vibe_config, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False)
        print("✅ Created default Vibe config")
    else:
        print("✅ Vibe config exists")

def fix_macos_use_tools():
    """Fix missing macos-use tools"""
    print("🔧 Checking macos-use tools...")

    # Check if binary exists
    HOME = os.path.expanduser("~")
    PROJECT_ROOT = os.path.join(HOME, "Documents/GitHub/atlastrinity")
    binary_path = os.path.join(
        PROJECT_ROOT, "vendor/mcp-server-macos-use/.build/release/mcp-server-macos-use"
    )
    if not os.path.exists(binary_path):
        print("❌ macos-use binary not found")
        print("🔨 Building macos-use...")

        build_script = os.path.join(PROJECT_ROOT, "vendor/mcp-server-macos-use/build.sh")
        if os.path.exists(build_script):
            import subprocess

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
        else:
            print("❌ Build script not found")
    else:
        print("✅ macos-use binary exists")

def fix_database_permissions():
    """Fix database file permissions"""
    print("🔧 Fixing database permissions...")

    db_dir = os.path.expanduser("~/.config/atlastrinity")
    if os.path.exists(db_dir):

        try:
            subprocess.run(["chmod", "-R", "755", db_dir], check=True)
            print("✅ Database permissions fixed")
        except Exception as e:
            print(f"❌ Permission fix failed: {e}")
    else:
        print("❌ Database directory not found")

def fix_log_rotation():
    """Fix log rotation to prevent oversized logs"""
    print("🔧 Setting up log rotation...")

    logs_dir = os.path.expanduser("~/.config/atlastrinity/logs")
    if os.path.exists(logs_dir):
        brain_log = os.path.join(logs_dir, "brain.log")
        if os.path.exists(brain_log):
            # Check log size
            size_mb = os.path.getsize(brain_log) / (1024 * 1024)
            if size_mb > 50:  # If log is larger than 50MB
                # Rotate log
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                old_log = f"{brain_log}.{timestamp}"
                os.rename(brain_log, old_log)
                print(f"✅ Rotated brain.log ({size_mb:.1f}MB) -> {old_log}")
            else:
                print(f"✅ Brain log size OK ({size_mb:.1f}MB)")
        else:
            print("⚠️ Brain log not found")
    else:
        print("⚠️ Logs directory not found")

def fix_memory_usage():
    """Fix high memory usage issues"""
    print("🔧 Checking memory usage...")

    HOME = os.path.expanduser("~")
    PROJECT_ROOT = os.path.join(HOME, "Documents/GitHub/atlastrinity")

    try:
        import psutil

        memory = psutil.virtual_memory()
        if memory.percent > 85:
            print(f"⚠️ High memory usage: {memory.percent}%")

            # Clear Python cache

            try:
                subprocess.run(
                    [
                        "find",
                        PROJECT_ROOT,
                        "-name",
                        "__pycache__",
                        "-type",
                        "d",
                        "-exec",
                        "rm",
                        "-rf",
                        "{}",
                        "+",
                    ],
                    check=False,
                )
                print("✅ Cleared Python cache")
            except:
                pass

            # Clear node_modules cache if needed
            node_modules = os.path.join(PROJECT_ROOT, "node_modules")
            if os.path.exists(node_modules):
                cache_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, _, filenames in os.walk(node_modules)
                    for filename in filenames
                ) / (1024 * 1024)
                if cache_size > 1000:  # If node_modules > 1GB
                    print(f"⚠️ Large node_modules: {cache_size:.1f}MB")
                    print("💡 Consider running 'npm ci' to clean up")
        else:
            print(f"✅ Memory usage OK: {memory.percent}%")
    except ImportError:
        print("⚠️ psutil not available - cannot check memory")
    except Exception as e:
        print(f"❌ Memory check failed: {e}")

def fix_git_permissions():
    """Fix git repository permissions"""
    print("🔧 Fixing git permissions...")

    HOME = os.path.expanduser("~")
    PROJECT_ROOT = os.path.join(HOME, "Documents/GitHub/atlastrinity")
    git_dir = os.path.join(PROJECT_ROOT, ".git")
    if os.path.exists(git_dir):

        try:
            # Fix git hooks permissions
            hooks_dir = os.path.join(git_dir, "hooks")
            if os.path.exists(hooks_dir):
                subprocess.run(
                    ["chmod", "+x", os.path.join(hooks_dir, "*")], shell=True, check=False
                )
                print("✅ Git hooks permissions fixed")

            # Check git remote
            result = subprocess.run(
                ["git", "remote", "-v"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
            )
            if "origin" in result.stdout:
                print("✅ Git remote configured")
            else:
                print("⚠️ Git remote not configured")
        except Exception as e:
            print(f"❌ Git fix failed: {e}")
    else:
        print("⚠️ Not a git repository")

def main():
    """Run all auto-fixes"""
    print("🔧 AtlasTrinity Auto-Fix Script")
    print("=" * 40)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()

    fixes = [
        ("Vibe Rate Limiting", fix_vibe_rate_limit),
        ("macOS Tools", fix_macos_use_tools),
        ("Database Permissions", fix_database_permissions),
        ("Log Rotation", fix_log_rotation),
        ("Memory Usage", fix_memory_usage),
        ("Git Permissions", fix_git_permissions),
    ]

    for name, fix_func in fixes:
        try:
            print(f"🔄 {name}...")
            fix_func()
            print()
        except Exception as e:
            print(f"❌ {name} failed: {e}")
            print()

    print("🎉 Auto-fix completed!")
    print("💡 Run 'python3 scripts/system_health_check.py' to verify fixes")

if __name__ == "__main__":
    main()
