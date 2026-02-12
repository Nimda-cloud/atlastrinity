"""Backward-compat shim: brain.mcp_manager → brain.mcp.mcp_manager"""
from brain.mcp.mcp_manager import *  # noqa: F401,F403
from brain.mcp.mcp_manager import MCPManager, mcp_manager  # noqa: F401
