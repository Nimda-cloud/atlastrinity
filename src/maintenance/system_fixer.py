"""
System Fixer Module
Consolidates auto-fix and error-fixing logic for AtlasTrinity.
"""

import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Add project root to path if needed (though this is in src now, so relative imports should work if run as module)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class SystemFixer:
    """Manages system health checks and auto-fixes."""

    def __init__(self):
        self.home = Path.home()
        self.config_root = self.home / ".config" / "atlastrinity"
        self.project_root = PROJECT_ROOT
        self.logs_dir = self.config_root / "logs"

    def run_all(self):
        """Run all registered fixers."""

        fixes = [
            ("Tool Routing", self.fix_tool_routing),
            ("Database Issues", self.fix_database_issues),
            ("macOS Tools", self.fix_macos_use_tools),
            ("Vibe Rate Limiting", self.fix_vibe_rate_limit),
            ("Log Rotation", self.fix_log_rotation),
            ("Memory Usage", self.fix_memory_usage),
            ("Git Permissions", self.fix_git_permissions),
            ("CI/CD Failures", self.fix_ci_failures),
        ]

        for _, fix_func in fixes:
            try:
                fix_func()
            except Exception:
                pass

    def fix_tool_routing(self):
        """Check and fix tool routing configuration."""
        dispatcher_file = self.project_root / "src/brain/tool_dispatcher.py"
        if dispatcher_file.exists():
            content = dispatcher_file.read_text(encoding="utf-8")

            checks = {
                '"get_clipboard": "macos-use_get_clipboard"': "get_clipboard",
                '"take_screenshot": "macos-use_take_screenshot"': "take_screenshot",
                '"analyze_screen": "macos-use_analyze_screen"': "analyze_screen",
            }

            for pattern, _ in checks.items():
                if pattern in content:
                    pass
                else:
                    pass
        else:
            pass

    def fix_database_issues(self):
        """Check database accessibility and structure."""
        # 1. Fix permissions
        if self.config_root.exists():
            try:
                subprocess.run(["chmod", "-R", "755", str(self.config_root)], check=True)
            except Exception:
                pass

        # 2. Check DB files
        db_paths = [
            self.config_root / "atlastrinity.db",
            self.config_root / "database.db",
            self.project_root / "data/atlastrinity.db",
        ]

        db_file = next((p for p in db_paths if p.exists()), None)

        if not db_file:
            return

        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            [t[0] for t in cursor.fetchall()]

            conn.close()
        except Exception:
            pass

    def fix_macos_use_tools(self):
        """Ensure macos-use MCP server is built and available."""
        binary_path = self.project_root / "vendor/mcp-server-macos-use/mcp-server-macos-use"

        if binary_path.exists():
            try:
                subprocess.run([str(binary_path), "--help"], capture_output=True, timeout=5)
            except Exception:
                pass
        else:
            build_script = self.project_root / "vendor/mcp-server-macos-use/build.sh"
            if build_script.exists():
                try:
                    subprocess.run(["bash", str(build_script)], check=True, timeout=300)
                except Exception:
                    pass
            else:
                pass

    def fix_vibe_rate_limit(self):
        """Ensure Vibe configuration exists."""
        vibe_config = self.config_root / "vibe_config.yaml"
        if not vibe_config.exists():
            default_config = {
                "rate_limit": {"requests_per_minute": 60, "burst_size": 10, "retry_delay": 10},
                "timeout": {"default": 60, "long_running": 3600},
            }
            with open(vibe_config, "w") as f:
                yaml.dump(default_config, f, default_flow_style=False)
        else:
            pass

    def fix_log_rotation(self):
        """Rotate logs if they are too large."""
        if not self.logs_dir.exists():
            return

        brain_log = self.logs_dir / "brain.log"
        if brain_log.exists():
            size_mb = brain_log.stat().st_size / (1024 * 1024)
            if size_mb > 50:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                old_log = self.logs_dir / f"brain.log.{timestamp}"
                brain_log.rename(old_log)
            else:
                pass

    def fix_memory_usage(self):
        """Check memory usage and clean cache if needed."""
        try:
            import psutil

            memory = psutil.virtual_memory()
            if memory.percent > 85:
                self._clear_caches()
            else:
                pass
        except ImportError:
            pass

    def _clear_caches(self):
        """Clear Python and Node caches."""
        # Clear __pycache__
        subprocess.run(
            [
                "find",
                str(self.project_root),
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

    def fix_ci_failures(self):
        """Monitor and fix CI/CD failures automatically."""
        # 1. Check local CI logs
        ci_logs = self.logs_dir / "ci_pipeline.log"
        if ci_logs.exists() and ci_logs.stat().st_size > 0:
            content = ci_logs.read_text(encoding="utf-8")
            if "script not found" in content.lower():
                # Trigger a scan for missing scripts
                subprocess.run([sys.executable, "src/maintenance/diagnostics.py"], check=False)

        # 2. Check for broken path patterns in workflow files
        workflows_dir = self.project_root / ".github/workflows"
        if workflows_dir.exists():
            for wf in workflows_dir.glob("*.yml"):
                content = wf.read_text(encoding="utf-8")
                if "scripts/ci/" in content:
                    # Automatically fix the path if we know where they are
                    if (self.project_root / "src/testing/ci").exists():
                        new_content = content.replace("scripts/ci/", "src/testing/ci/")
                        wf.write_text(new_content, encoding="utf-8")

    def fix_git_permissions(self):
        """Fix git hook permissions."""
        git_dir = self.project_root / ".git"
        if git_dir.exists():
            hooks_dir = git_dir / "hooks"
            if hooks_dir.exists():
                subprocess.run(["chmod", "+x", *map(str, hooks_dir.glob("*"))], check=False)


if __name__ == "__main__":
    fixer = SystemFixer()
    fixer.run_all()
