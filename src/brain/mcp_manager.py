"""Backward-compat shim: brain.mcp_manager → brain.mcp.mcp_manager"""

from brain.mcp.mcp_manager import MCPManager, mcp_manager  # noqa: F401

__all__ = ["MCPManager", "mcp_manager"]
