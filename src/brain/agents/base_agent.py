"""
BaseAgent - Shared utilities for Trinity agents

This module provides common functionality used by Atlas, Tetyana, and Grisha agents.
"""

import json
from typing import Any, Dict

class BaseAgent:
    """Base class for Trinity agents with shared utilities."""
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM with fuzzy fallback.
        
        Handles:
        1. Clean JSON responses
        2. JSON embedded in text
        3. YAML-like key:value pairs
        4. Raw text fallback
        """
        # 1. Try standard JSON extraction
        try:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass

        # 2. Fuzzy YAML-like parsing (handles LLM responses like "verified: true\nconfidence: 0.9")
        try:
            data = {}
            for line in content.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    # Handle boolean values
                    if value.lower() == "true":
                        data[key] = True
                    elif value.lower() == "false":
                        data[key] = False
                    # Handle numeric values
                    elif value.replace(".", "", 1).isdigit():
                        data[key] = float(value)
                    else:
                        data[key] = value
            
            # Consider it valid fuzzy parse if we found key fields
            if "verified" in data or "intent" in data or "success" in data:
                return data
        except Exception:
            pass

        # 3. Return raw content as fallback
        return {"raw": content}

    async def use_sequential_thinking(self, task: str, total_thoughts: int = 3) -> Dict[str, Any]:
        """
        Universal reasoning capability for any agent.
        Uses the 'sequential-thinking' MCP tool to break down complex problems.
        """
        from ..mcp_manager import mcp_manager
        from ..logger import logger
        
        agent_name = self.__class__.__name__.upper()
        logger.info(f"[{agent_name}] 🤔 Thinking deeply about: {task[:60]}...")
        
        full_analysis = ""
        
        try:
            # Check availability first (optimization)
            # We assume mcp_manager handles connection state, but quick check prevents errors
            pass 

            for i in range(1, total_thoughts + 1):
                is_last = (i == total_thoughts)
                
                # Step thought
                logger.debug(f"[{agent_name}] Thought cycle {i}/{total_thoughts}")
                result = await mcp_manager.dispatch_tool(
                    "sequential-thinking.sequentialthinking",
                    {
                        "thought": f"Analysis step {i}/{total_thoughts} for: {task}",
                        "thoughtNumber": i,
                        "totalThoughts": total_thoughts,
                        "nextThoughtNeeded": not is_last
                    }
                )
                
                # Robust extraction of text content
                text_content = ""
                if isinstance(result, dict):
                    # Try creating human readable summary locally
                    text_content = str(result.get("content", result.get("result", "")))
                elif hasattr(result, "content"):
                     content_list = getattr(result, "content", [])
                     if isinstance(content_list, list):
                         parts = []
                         for c in content_list:
                             if hasattr(c, "text"): parts.append(c.text)
                             else: parts.append(str(c))
                         text_content = " ".join(parts)
                     else:
                         text_content = str(content_list)
                else:
                    text_content = str(result)
                
                full_analysis += f"\n[Thought {i}]: {text_content[:800]}..."
            
            logger.info(f"[{agent_name}] Reasoning complete.")
            return {"success": True, "analysis": full_analysis}

        except Exception as e:
            logger.warning(f"[{agent_name}] Sequential thinking unavailable/failed: {e}")
            # Do not crash the agent, just return failure so it can fallback to standard logic
            return {"success": False, "error": str(e), "analysis": full_analysis}
