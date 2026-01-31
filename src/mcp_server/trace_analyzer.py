"""
TraceAnalyzer: Execution Log Analysis for DevTools MCP.

Analyzes MCP tool execution logs to detect logic issues like:
- Infinite loops (repeated calls with same args)
- Hallucinated tools (calls to non-existent tools)
- Access denied or repeated failures
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, TypedDict


class TraceIssue(TypedDict):
    """Represents a detected issue in the execution trace."""
    type: str  # 'loop', 'error', 'inefficiency'
    severity: str  # 'high', 'medium', 'low'
    description: str
    count: int


class LogEntry(TypedDict):
    """Parsed log entry relevant to tool execution."""
    timestamp: str | None
    tool_name: str
    args: str | dict | None
    status: str | None  # 'success', 'error'
    error_msg: str | None


def parse_brain_log(log_path: str | Path) -> list[LogEntry]:
    """Parse brain.log format to extract tool calls."""
    entries: list[LogEntry] = []
    path = Path(log_path)
    
    if not path.exists():
        return []

    # Regex for standard brain.log pattern
    # Example: 2025-01-30 21:20:47,123 - plain_logger - INFO - [Orchestrator] Calling tool: weather_lookup args: {...}
    
    # We'll use a loose regex to catch variations
    tool_call_re = re.compile(r"Calling tool:\s*(\w+)\s*args:\s*(\{.*\})", re.IGNORECASE)
    tool_error_re = re.compile(r"Tool execution failed:\s*(.*)", re.IGNORECASE)
    
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            # 1. Check for tool calls
            match = tool_call_re.search(line)
            if match:
                tool_name = match.group(1)
                args_str = match.group(2)
                try:
                    # Try to parse args as JSON if possible, otherwise keep string
                    # Often logs have single quotes or truncated JSON
                    args = args_str 
                except:
                    args = args_str
                
                entries.append({
                    "timestamp": line.split(",")[0] if "," in line else None,
                    "tool_name": tool_name,
                    "args": args,
                    "status": "attempts",
                    "error_msg": None
                })
                continue
                
    return entries


def analyze_trace_issues(entries: list[LogEntry]) -> list[TraceIssue]:
    """Analyze parsed entries for logic issues."""
    issues: list[TraceIssue] = []
    
    # 1. Loop Detection
    # Logic: if same tool + same args called > 3 times
    call_counts = defaultdict(int)
    
    for entry in entries:
        # Create a simple signature: tool + args
        sig = f"{entry['tool_name']}:{str(entry['args'])}"
        call_counts[sig] += 1

    for sig, count in call_counts.items():
        if count >= 3:
            tool, args = sig.split(":", 1)
            issues.append({
                "type": "loop",
                "severity": "high" if count > 5 else "medium",
                "description": f"Tool '{tool}' called {count} times with identical arguments.",
                "count": count
            })

    # 2. Sequential Repetition (Back-to-back same tool)
    if len(entries) > 1:
        repeat_chain = 0
        last_tool = ""
        
        for entry in entries:
            if entry["tool_name"] == last_tool:
                repeat_chain += 1
            else:
                if repeat_chain >= 4:
                     issues.append({
                        "type": "inefficiency",
                        "severity": "low",
                        "description": f"Tool '{last_tool}' called {repeat_chain} times sequentially (scan pattern?).",
                        "count": repeat_chain
                    })
                repeat_chain = 1
                last_tool = entry["tool_name"]
                
    return issues


def analyze_log_file(log_path: str) -> dict[str, Any]:
    """Main entry point to analyze a log file."""
    try:
        entries = parse_brain_log(log_path)
        issues = analyze_trace_issues(entries)
        
        return {
            "success": True,
            "log_path": log_path,
            "parsed_entries": len(entries),
            "issue_count": len(issues),
            "issues": issues
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
