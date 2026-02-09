"""
VIBE Proxy Servers
=================

Specialized OpenAI-compatible proxy servers for VIBE CLI.
Each proxy handles a specific LLM provider for optimal performance and stability.

Available Proxies:
- copilot_vibe_proxy.py: GitHub Copilot proxy (port 8086)
- vibe_windsurf_proxy.py: Windsurf/Codeium proxy (port 8085)

Usage:
    from providers.proxy import CopilotVibeProxy, WindsurfVibeProxy
"""

from .copilot_vibe_proxy import CopilotVibeProxyHandler
from .vibe_windsurf_proxy import VibeWindsurfProxyHandler

__all__ = [
    "CopilotVibeProxyHandler",
    "VibeWindsurfProxyHandler",
]
