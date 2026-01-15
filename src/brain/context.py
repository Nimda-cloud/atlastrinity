"""
AtlasTrinity Shared Context

Singleton module for sharing context between all agents.
Solves the problem of agents using wrong paths or lacking awareness
of the current working directory and recent operations.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

# Get the actual user home directory
ACTUAL_HOME = os.path.expanduser("~")
GITHUB_ROOT = f"{ACTUAL_HOME}/Documents/GitHub"


@dataclass
class SharedContext:
    """
    Shared context singleton that all agents can access.

    Provides:
    - Current working directory awareness
    - Recent file tracking
    - Last successful path memory
    - Project context
    """

    # Core path context - uses actual user home directory
    current_working_directory: str = GITHUB_ROOT
    active_project: str = ""
    last_successful_path: str = ""

    # File tracking
    recent_files: List[str] = field(default_factory=list)
    created_directories: List[str] = field(default_factory=list)

    # Operation history (for debugging)
    operation_count: int = 0
    last_operation: str = ""
    last_update: Optional[datetime] = None
    available_tools_summary: str = ""

    def __post_init__(self):
        # Auto-detect CWD on startup
        try:
            cwd = os.getcwd()
            if "/Documents/GitHub/" in cwd:
                self.current_working_directory = cwd
                self.last_successful_path = cwd
                # Infer project
                parts = cwd.split("/Documents/GitHub/")
                if len(parts) > 1:
                    self.active_project = parts[1].split("/")[0]
        except Exception:
            pass

    def update_path(self, path: str, operation: str = "access") -> None:
        """
        Update context with a new successful path.
        Called by agents after successful operations.
        """
        if path and (path.startswith("/Users") or path.startswith("~")):
            path = os.path.expandvars(os.path.expanduser(path))
            self.last_successful_path = path

            # Infer project from path
            if "/Documents/GitHub/" in path:
                parts = path.split("/Documents/GitHub/")
                if len(parts) > 1:
                    project_part = parts[1].split("/")[0]
                    if project_part:
                        self.active_project = project_part
                        self.current_working_directory = f"{GITHUB_ROOT}/{project_part}"

            # Track files
            if operation in ["create", "write", "read"]:
                if path not in self.recent_files:
                    self.recent_files.append(path)
                    # Keep only last 20 files
                    if len(self.recent_files) > 20:
                        self.recent_files = self.recent_files[-20:]

            # Track directories
            if operation == "create_directory":
                if path not in self.created_directories:
                    self.created_directories.append(path)

            self.operation_count += 1
            self.last_operation = f"{operation}: {path}"
            self.last_update = datetime.now()

    def get_best_path(self, hint: str = "") -> str:
        """
        Get the most likely correct path based on context.
        Used by agents to auto-correct placeholder paths.
        """
        # If we have an active project, use that
        if self.active_project:
            return self.current_working_directory

        # If we have a last successful path, use its directory
        if self.last_successful_path:
            import os

            return os.path.dirname(self.last_successful_path)

        # Default to GitHub directory
        return GITHUB_ROOT

    def resolve_path(self, raw_path: str) -> str:
        """
        Resolve a potentially invalid path to a valid one.
        Handles placeholders, tilde, relative paths.
        """
        if not raw_path:
            return self.get_best_path()

        raw_path = os.path.expandvars(raw_path)

        # Expand tilde
        if raw_path.startswith("~/"):
            raw_path = raw_path.replace("~/", f"{ACTUAL_HOME}/")
        elif raw_path == "~":
            raw_path = ACTUAL_HOME

        # Check for placeholder patterns
        placeholder_patterns = ["/path/", "/to/", "${", "{{"]
        if any(p in raw_path for p in placeholder_patterns):
            return self.get_best_path()

        # Check for valid absolute path
        if not raw_path.startswith("/Users"):
            # Relative path - prepend working directory
            return f"{self.current_working_directory}/{raw_path.lstrip('/')}"

        return raw_path

    def to_dict(self) -> dict:
        """Export context for logging or debugging."""
        return {
            "cwd": self.current_working_directory,
            "project": self.active_project,
            "last_path": self.last_successful_path,
            "recent_files": self.recent_files[-5:],
            "operation_count": self.operation_count,
            "last_op": self.last_operation,
        }


# Singleton instance - import this in other modules
shared_context = SharedContext()
