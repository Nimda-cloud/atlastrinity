#!/usr/bin/env python3
"""
Ultimate Analysis of All 45 macOS Use MCP Tools
Find maximum improvement opportunities
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

# Add src to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent / "src"))

try:
    from src.brain.mcp.mcp_manager import MCPManager  # noqa: E402
except ImportError:
    MCPManager = None


async def ultimate_analysis():
    """Повний аналіз всіх інструментів та генерація ультимативного звіту."""
    print("Запуск ультимативного аналізу інструментів...")

    if not MCPManager:
        print("Error: MCPManager not found")
        return []

    manager = MCPManager()
    tools = await manager.list_tools("macos-use")

    ultimate_improvements = []
    for tool in tools:
        imp = _analyze_single_tool(tool)
        if imp:
            ultimate_improvements.append(imp)

    _print_priority_analysis(ultimate_improvements)
    return ultimate_improvements


def _analyze_single_tool(tool: Any) -> dict[str, Any] | None:
    name = f"{getattr(tool, 'name', str(tool))}"
    improvements = []

    # Typing
    if "type" in name.lower():
        improvements.extend(["Add typing speed control", "Add auto-correct", "Add templates"])
    # Click
    elif "click" in name.lower():
        improvements.extend(["Add heatmaps", "Add gestures", "Add feedback"])
    # Window
    elif "window" in name.lower():
        improvements.extend(["Add layouts", "Add workspaces", "Add animations"])
    # Finder
    elif "finder" in name.lower():
        improvements.extend(["Add search indexing", "Add batch ops", "Add encryption"])

    if improvements:
        return {"tool": name, "improvements": improvements, "improvement_count": len(improvements)}
    return None


def _print_priority_analysis(ultimate_improvements: list[dict[str, Any]]):
    priority_areas = ["AI", "Security", "UX", "Performance"]
    for area in priority_areas:
        relevant = [
            imp["tool"]
            for imp in ultimate_improvements
            if any(area.lower() in str(i).lower() for i in imp["improvements"])
        ]
        if relevant:
            print(f"Area: {area} - Tools: {', '.join(relevant[:3])}")


if __name__ == "__main__":
    asyncio.run(ultimate_analysis())
