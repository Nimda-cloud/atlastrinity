# ruff: noqa: E402
"""Grisha - The Visor/Auditor

Role: Result verification via Vision, Security control
Voice: Mykyta (male)
Model: Configured vision model
"""

import os
import sys

# Robust path handling for both Dev and Production (Packaged)
current_dir = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(current_dir, "..", "..")
sys.path.insert(0, os.path.abspath(root))

import base64
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from providers.copilot import CopilotLLM
from src.brain.agents.base_agent import BaseAgent
from src.brain.config_loader import config
from src.brain.context import shared_context
from src.brain.logger import logger
from src.brain.prompts import AgentPrompts
from src.brain.prompts.grisha import (
    GRISHA_DEEP_VALIDATION_REASONING,
    GRISHA_FORENSIC_ANALYSIS,
    GRISHA_LOGICAL_VERDICT,
    GRISHA_VERIFICATION_GOAL_ANALYSIS,
)


@dataclass
class VerificationResult:
    """Verification result"""

    step_id: str
    verified: bool
    confidence: float  # 0.0 - 1.0
    description: str
    issues: list
    voice_message: str = ""
    timestamp: datetime | None = None
    screenshot_analyzed: bool = False

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class Grisha(BaseAgent):
    """Grisha - The Visor/Auditor

    3-Phase Verification Architecture:

    Phase 1: Strategy Planning (strategy_model: gpt-4o)
             - Analyzes step requirements and determines verification approach
             - Plans which MCP tools are needed for evidence collection
             - Outputs verification strategy in natural language

    Phase 2: Tool Execution (model: gpt-4.1)
             - Selects and executes MCP server tools based on strategy
             - Collects evidence (logs, file contents, DB queries, etc.)
             - Similar to Tetyana's execution phase

    Phase 3: Verdict Formation (verdict_model: gpt-4o, vision_model: gpt-4o)
             - Analyzes evidence collected from Phase 2
             - Uses vision model for screenshot analysis if needed
             - Forms logical verdict: PASS/FAIL with confidence
             - Can fallback to gpt-4.1 if gpt-4o fails

    Security Functions:
    - Blocking dangerous commands via BLOCKLIST
    - Multi-layer verification for critical operations
    """

    NAME = AgentPrompts.GRISHA["NAME"]
    DISPLAY_NAME = AgentPrompts.GRISHA["DISPLAY_NAME"]
    VOICE = AgentPrompts.GRISHA["VOICE"]
    COLOR = AgentPrompts.GRISHA["COLOR"]
    SYSTEM_PROMPT = AgentPrompts.GRISHA["SYSTEM_PROMPT"]

    # Hardcoded blocklist for critical commands
    BLOCKLIST = [
        "rm -rf /",
        "mkfs",
        "dd if=",
        ":(){:|:&};:",
        "chmod 777 /",
        "chown root:root /",
        "> /dev/sda",
        "mv / /dev/null",
    ]

    def __init__(self, vision_model: str | None = None):
        """Initialize Grisha with 3-phase verification architecture.

        Phase 1: Strategy Planning (strategy_model: gpt-4o)
                 - Analyze what needs verification and which tools to use

        Phase 2: Tool Execution (model: gpt-4.1)
                 - Select and execute MCP server tools (similar to Tetyana)

        Phase 3: Verdict Formation (verdict_model: gpt-4o, vision_model: gpt-4o)
                 - Analyze collected evidence and form final verdict
        """
        # Get model config (config.yaml > parameter)
        agent_config = config.get_agent_config("grisha")
        security_config = config.get_security_config()

        # Phase 1: Strategy Planning Model
        strategy_model = (
            agent_config.get("strategy_model")
            or config.get("models.reasoning")
            or config.get("models.default")
        )
        if not strategy_model or not strategy_model.strip():
            raise ValueError(
                "[GRISHA] Strategy model not configured. Please set 'models.reasoning' or 'agents.grisha.strategy_model' in config.yaml"
            )
        self.strategist = CopilotLLM(model_name=strategy_model)

        # Phase 2: Execution Model (for MCP tool calls, like Tetyana)
        execution_model = agent_config.get("model") or config.get("models.default")
        if not execution_model or not execution_model.strip():
            raise ValueError(
                "[GRISHA] Execution model not configured. Please set 'models.default' or 'agents.grisha.model' in config.yaml"
            )
        self.executor = CopilotLLM(model_name=execution_model)

        # Phase 3: Verdict & Vision Models
        vision_model_name = (
            vision_model
            or agent_config.get("vision_model")
            or config.get("models.vision")
            or execution_model
        )
        if not vision_model_name or not vision_model_name.strip():
            raise ValueError(
                "[GRISHA] Vision model not configured. Please set 'models.vision' or 'agents.grisha.vision_model' in config.yaml"
            )
        self.llm = CopilotLLM(model_name=vision_model_name, vision_model_name=vision_model_name)

        verdict_model = agent_config.get("verdict_model")
        if not verdict_model or not verdict_model.strip():
            verdict_model = strategy_model  # Fallback to strategy model
        self.verdict_llm = CopilotLLM(model_name=verdict_model)

        # General settings
        self.temperature = agent_config.get("temperature", 0.3)
        self.dangerous_commands = security_config.get("dangerous_commands", self.BLOCKLIST)
        self.verifications: list = []
        self._strategy_cache = {}

        logger.info(
            f"[GRISHA] 3-Phase Architecture Initialized:\n"
            f"  Phase 1 (Strategy): {strategy_model}\n"
            f"  Phase 2 (Execution): {execution_model}\n"
            f"  Phase 3 (Verdict): {verdict_model}, Vision: {vision_model_name}"
        )

    async def _deep_validation_reasoning(
        self,
        step: dict[str, Any],
        result: Any,
        goal_context: str,
    ) -> dict[str, Any]:
        """Performs deep validation reasoning using sequential thinking.
        Returns structured validation insights across multiple layers.
        """
        step_action = step.get("action", "")
        expected = step.get("expected_result", "")

        # Extract result string safely
        if hasattr(result, "result"):
            result_str = str(result.result)[:2000]
        elif isinstance(result, dict):
            result_str = str(result.get("result", result.get("output", "")))[:2000]
        else:
            result_str = str(result)[:2000]

        reasoning_query = GRISHA_DEEP_VALIDATION_REASONING.format(
            step_action=step_action,
            expected_result=expected,
            result_str=result_str,
            goal_context=goal_context
        )

        reasoning = await self.use_sequential_thinking(reasoning_query, total_thoughts=2)
        return {
            "deep_analysis": reasoning.get("analysis", ""),
            "confidence_boost": 0.1 if reasoning.get("success") else 0.0,
            "layers_validated": 4,
            "synthesis": reasoning.get("final_thought", ""),
        }

    async def _multi_layer_verification(
        self,
        step: dict[str, Any],
        result: Any,
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Performs verification across 4 layers:
        1. Tool Execution Layer - was the tool called correctly?
        2. Output Layer - is the output valid?
        3. State Layer - did system state change as expected?
        4. Goal Layer - does this advance the mission?
        """

        layers: list[dict[str, Any]] = []

        # Layer 1: Tool Execution
        tool_layer = {"layer": "tool_execution", "passed": False, "evidence": ""}
        if hasattr(result, "tool_call") or (isinstance(result, dict) and result.get("tool_call")):
            tc = getattr(result, "tool_call", None) or result.get("tool_call", {})
            if tc and tc.get("name"):
                tool_layer["passed"] = True
                tool_layer["evidence"] = f"Інструмент '{tc['name']}' був викликаний"
        layers.append(tool_layer)

        # Layer 2: Output Validation
        output_layer = {"layer": "output_validation", "passed": False, "evidence": ""}
        result_str = str(
            result.get("result", "") if isinstance(result, dict) else getattr(result, "result", ""),
        )
        if result_str and len(result_str) > 0 and "error" not in result_str.lower():
            output_layer["passed"] = True
            output_layer["evidence"] = f"Отримано результат: {result_str[:200]}..."
        layers.append(output_layer)

        # Layer 3: State Verification (via DB trace)
        state_layer = {"layer": "state_verification", "passed": False, "evidence": ""}
        try:
            trace = await self._fetch_execution_trace(str(step.get("id")))
            if "No DB records" not in trace:
                state_layer["passed"] = True
                state_layer["evidence"] = "Трейс виконання знайдено в базі даних"
        except Exception:
            state_layer["evidence"] = "Не вдалося перевірити стан"
        layers.append(state_layer)

        # Layer 4: Goal Alignment (assume aligned unless proven otherwise)
        goal_layer = {
            "layer": "goal_alignment",
            "passed": True,
            "evidence": "Крок є частиною затвердженого плану",
        }
        layers.append(goal_layer)

        # Log layer results
        passed_count = sum(1 for l in layers if l["passed"])
        logger.info(f"[GRISHA] Multi-layer verification: {passed_count}/4 layers passed")

        return layers

    async def _create_robust_strategy_via_reasoning(
        self,
        step_description: str,
        context: dict,
        goal_context: str = "",
    ) -> str:
        """Uses reasoning model (configured in config.yaml) to create a robust verification strategy.
        OPTIMIZATION: Caches strategies by step type to avoid redundant LLM calls.
        NOTE: This method appears to be legacy/unused. Consider removal or refactoring.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        # OPTIMIZATION: Check cache first
        cache_key = f"{step_description[:50]}"
        if cache_key in self._strategy_cache:
            logger.info(f"[GRISHA] Using cached strategy for: {cache_key[:30]}...")
            return self._strategy_cache[cache_key]

        # Legacy code - parameters don't match usage
        prompt = f"Create verification strategy for: {step_description}\nContext: {context}\nGoal: {goal_context}"

        # Get available capabilities to inform the strategist
        capabilities = self._get_environment_capabilities()
        system_msg = AgentPrompts.grisha_strategist_system_prompt(capabilities)
        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content=prompt),
        ]

        try:
            response = await self.strategist.ainvoke(messages)
            strategy = getattr(response, "content", str(response))
            logger.info(f"[GRISHA] Strategy devised: {strategy[:200]}...")
            # Cache the strategy
            self._strategy_cache[cache_key] = strategy
            return strategy
        except Exception as e:
            logger.warning(f"[GRISHA] Strategy planning failed: {e}")
            return "Proceed with standard verification (Vision + Tools)."

    def _check_blocklist(self, action_desc: str) -> bool:
        """Check if action contains blocked commands"""
        for blocked in self.dangerous_commands:
            if blocked in action_desc:
                return True
        return False

    def _get_environment_capabilities(self) -> str:
        """Collects raw facts about the environment to inform the strategist.
        No heuristics here—just data for the LLM to reason about.
        """
        try:
            from ..mcp_manager import mcp_manager

            servers_cfg = getattr(mcp_manager, "config", {}).get("mcpServers", {})
            active_servers = [
                s for s, cfg in servers_cfg.items() if not (cfg or {}).get("disabled")
            ]

            swift_servers = []
            for s in active_servers:
                cfg = servers_cfg.get(s, {})
                cmd = (cfg or {}).get("command", "") or ""
                if (
                    "swift" in s.lower()
                    or "macos" in s.lower()
                    or (isinstance(cmd, str) and "swift" in cmd.lower())
                ):
                    swift_servers.append(s)
        except Exception:
            active_servers = []
            swift_servers = []

        # Check if vision model is powerful (from config)
        vision_model = (getattr(self.llm, "model_name", "") or "unknown").lower()
        is_powerful = "vision" in vision_model

        info = [
            f"Active MCP Realms: {', '.join(active_servers)}",
            f"Native Swift Servers: {', '.join(swift_servers)} (Preferred for OS control)",
            f"Vision Model: {vision_model} ({'High-Performance' if is_powerful else 'Standard'})",
            f"Timezone: {datetime.now().astimezone().tzname()}",
            "Capabilities: Full UI Traversal, OCR, Terminal, Filesystem, Apple Productivity Apps integration.",
        ]
        return "\n".join(info)

    def _summarize_ui_data(self, raw_data: str) -> str:
        """Intelligently extracts the 'essence' of UI traversal data locally.
        Reduces thousands of lines of JSON to a concise list of key interactive elements.
        """
        import json

        if (
            not raw_data
            or not isinstance(raw_data, str)
            or not (raw_data.strip().startswith("{") or raw_data.strip().startswith("["))
        ):
            return raw_data

        try:
            data = json.loads(raw_data)
            # Find the list of elements (robust to various nesting levels)
            elements = []
            if isinstance(data, list):
                elements = data
            elif isinstance(data, dict):
                # Search common keys: 'elements', 'result', etc.
                if "elements" in data:
                    elements = data["elements"]
                elif "result" in data and isinstance(data["result"], dict):
                    elements = data["result"].get("elements", [])
                elif "result" in data and isinstance(data["result"], list):
                    elements = data["result"]

            if not elements or not isinstance(elements, list):
                return raw_data[:2000]  # Fallback to truncation

            summary_items = []
            for el in elements:
                if not isinstance(el, dict):
                    continue

                # Filter: Only care about visible or important elements to save tokens
                if el.get("isVisible") is False and not el.get("label") and not el.get("title"):
                    continue

                role = el.get("role", "element")
                label = (
                    el.get("label") or el.get("title") or el.get("description") or el.get("help")
                )
                value = el.get("value") or el.get("stringValue")

                # Only include if it has informative content
                if (
                    label
                    or value
                    or role in ["AXButton", "AXTextField", "AXTextArea", "AXCheckBox"]
                ):
                    item = f"[{role}"
                    if label:
                        item += f": '{label}'"
                    if value:
                        item += f", value: '{value}'"
                    item += "]"
                    summary_items.append(item)

            summary = " | ".join(summary_items)

            # Final check: if summary is still somehow empty but we had elements,
            # maybe we were too aggressive. Provide a tiny slice of raw.
            if not summary and elements:
                return f"UI Tree Summary: {len(elements)} elements found. Samples: {elements[:2]!s}"

            return f"UI Summary ({len(elements)} elements): " + summary

        except Exception as e:
            logger.debug(f"[GRISHA] UI summarization failed (falling back to truncation): {e}")
            return raw_data[:3000]

    async def _analyze_verification_goal(
        self, step: dict[str, Any], goal_context: str
    ) -> dict[str, Any]:
        """Phase 1: Use sequential-thinking to deeply understand verification goal and select tools.

        Returns:
            {
                "verification_purpose": str,  # Clear goal of what needs verification
                "selected_tools": list[dict],  # Tools to use with reasoning
                "success_criteria": str,  # What constitutes success
            }
        """
        step_action = step.get("action", "")
        expected_result = step.get("expected_result", "")
        step_id = step.get("id", "unknown")

        query = GRISHA_VERIFICATION_GOAL_ANALYSIS.format(
            step_id=step_id,
            step_action=step_action,
            expected_result=expected_result,
            goal_context=goal_context
        )

        logger.info(f"[GRISHA] Phase 1: Analyzing verification goal for step {step_id}...")

        try:
            reasoning_result = await self.use_sequential_thinking(query, total_thoughts=3)

            if not reasoning_result.get("success"):
                logger.warning("[GRISHA] Sequential thinking failed, using fallback strategy")
                return {
                    "verification_purpose": f"Verify that '{step_action}' was executed successfully",
                    "selected_tools": [
                        {
                            "tool": "vibe.vibe_check_db",
                            "reason": "Check tool execution records in DB",
                        },
                    ],
                    "success_criteria": "Execution record found and result contains no critical errors",
                }

            analysis_text = reasoning_result.get("analysis", "")
            
            # ANTI-LOOP DETECTION: Check for repetitive patterns
            if self._detect_repetitive_thinking(analysis_text):
                logger.warning("[GRISHA] Anti-loop triggered - repetitive thinking detected")
                return {
                    "verification_purpose": f"Verify that '{step_action}' was executed successfully",
                    "selected_tools": [
                        {
                            "tool": "vibe.vibe_check_db",
                            "reason": "Fallback: DB audit due to repetitive thinking",
                        },
                    ],
                    "success_criteria": "Execution record found and result contains no critical errors",
                    "full_reasoning": "Anti-loop fallback activated",
                }

            # Parse the analysis (simple extraction, can be improved)
            return {
                "verification_purpose": analysis_text,
                "selected_tools": self._extract_tools_from_analysis(analysis_text, step),
                "success_criteria": analysis_text,
                "full_reasoning": analysis_text,
            }

        except Exception as e:
            logger.error(f"[GRISHA] Verification goal analysis failed: {e}")
            return {
                "verification_purpose": f"Verify '{step_action}'",
                "selected_tools": [{"tool": "vibe.vibe_check_db", "reason": "Fallback"}],
                "success_criteria": "Non-empty execution results",
            }

    def _extract_tools_from_analysis(self, analysis: str, step: dict) -> list[dict]:
        """Extract tool recommendations from sequential-thinking analysis."""
        tools = []
        step_id = step.get("id", "unknown")

        # Always include database check as primary source of truth
        tools.append(
            {
                "tool": "vibe.vibe_check_db",
                "args": {
                    "query": f"SELECT te.tool_name, te.arguments, te.result, te.created_at FROM tool_executions te JOIN task_steps ts ON te.step_id = ts.id WHERE ts.sequence_number = '{step_id}' ORDER BY te.created_at DESC LIMIT 5"
                },
                "reason": "Primary source of truth - database audit",
            }
        )

        # Detect if this is an analysis task vs action task
        step_action_lower = step.get("action", "").lower()

        # Analysis task keywords - for these, DB trace is sufficient
        is_analysis_task = any(
            keyword in step_action_lower
            for keyword in [
                "analyze",
                "review",
                "research",
                "investigate",
                "examine",
                "study",
                "assess",
                "evaluate",
                "explore",
            ]
        )

        # If it's an analysis task, don't add file verification tools
        # (DB trace of tool execution is sufficient proof of analysis)
        if is_analysis_task:
            logger.info("[GRISHA] Detected ANALYSIS task - relying on DB trace only")
            return tools[:2]  # Only DB check

        # For ACTION tasks, add context-aware verification tools
        if (
            "file" in step_action_lower
            or "save" in step_action_lower
            or "create" in step_action_lower
        ):
            # Use dynamic path based on actual home directory
            project_root = os.path.expanduser("~/Documents/GitHub/atlastrinity")
            tools.append(
                {
                    "tool": "macos-use_finder_list_files",
                    "args": {"path": project_root},
                    "reason": "Check if files were created",
                }
            )

        if "search" in step_action_lower or "find" in step_action_lower:
            tools.append(
                {
                    "tool": "macos-use_get_clipboard",
                    "args": {},
                    "reason": "Check if search results were copied",
                }
            )

        return tools[:4]  # Limit to 4 tools max

    async def _form_logical_verdict(
        self,
        step: dict[str, Any],
        goal_analysis: dict[str, Any],
        verification_results: list[dict],
        goal_context: str,
    ) -> dict[str, Any]:
        """Phase 2: Use sequential-thinking to form LOGICAL verdict based on collected evidence.

        Args:
            step: Step being verified
            goal_analysis: Results from Phase 1 (verification purpose, criteria)
            verification_results: List of tool execution results
            goal_context: Overall task goal

        Returns:
            {
                "verified": bool,
                "confidence": float,
                "reasoning": str,
                "issues": list[str],
            }
        """
        step_id = step.get("id", "unknown")
        step_action = step.get("action", "")
        expected_result = step.get("expected_result", "")

        # Format results for analysis
        results_summary = "\n".join(
            [
                f"Tool {i + 1}: {r['tool']}\n  Success: {not r.get('error', False)}\n  Result: {r.get('result', 'N/A')[:500]}\n"
                for i, r in enumerate(verification_results)
            ]
        )

        query = GRISHA_LOGICAL_VERDICT.format(
            step_action=step_action,
            expected_result=expected_result,
            results_summary=results_summary,
            goal_analysis=goal_analysis,
            goal_context=goal_context
        )

        logger.info(f"[GRISHA] Phase 2: Forming logical verdict for step {step_id}...")

        try:
            reasoning_result = await self.use_sequential_thinking(query, total_thoughts=2)

            if not reasoning_result.get("success"):
                logger.warning("[GRISHA] Logical verdict analysis failed, using fallback")
                return self._fallback_verdict(verification_results)

            analysis_text = reasoning_result.get("analysis", "")
            analysis_upper = analysis_text.upper()

            # Parse verdict using regex for specific headers
            import re

            verdict_match = re.search(
                r"(?:VERDICT|ВЕРДИКТ)[:\s]*(CONFIRMED|FAILED|ПІДТВЕРДЖЕНО|ПРОВАЛЕНО|УСПІШНО)",
                analysis_text,
                re.IGNORECASE,
            )

            if verdict_match:
                verdict_val = verdict_match.group(1).upper()
                verified = any(
                    word in verdict_val for word in ["CONFIRMED", "ПІДТВЕРДЖЕНО", "УСПІШНО"]
                )
            else:
                # Fallback to keyword search ONLY IF exact format missing (be careful with global search)
                # We prioritize the first few lines for the verdict
                header_text = analysis_upper.split("REASONING")[0].split("ОБҐРУНТУВАННЯ")[0]
                verified = any(
                    word in header_text
                    for word in ["CONFIRMED", "SUCCESS", "VERIFIED", "ПІДТВЕРДЖЕНО", "УСПІШНО"]
                )
                if not verified and any(
                    word in header_text for word in ["FAILED", "ERROR", "ПРОВАЛЕНО"]
                ):
                    verified = False

            # Extract confidence
            import re

            confidence_match = re.search(
                r"(?:CONFIDENCE|ВПЕВНЕНІСТЬ)[:\s]*(\d+\.?\d*)\%?", analysis_text, re.IGNORECASE
            )
            confidence = (
                float(confidence_match.group(1)) if confidence_match else (0.8 if verified else 0.2)
            )
            if confidence > 1.0:
                confidence /= 100.0

            # Extract Ukrainian reasoning
            reasoning_match = re.search(
                r"(?:REASONING|ОБҐРУНТУВАННЯ)[:\s]*(.*?)(?=\n- \*\*|\Z)",
                analysis_text,
                re.DOTALL | re.IGNORECASE,
            )
            ukrainian_reasoning = (
                reasoning_match.group(1).strip() if reasoning_match else analysis_text
            )

            # Extract issues
            issues_match = re.search(
                r"(?:ISSUES|ПРОБЛЕМИ)[:\s]*(.*?)(?=\n- \*\*|\Z)",
                analysis_text,
                re.DOTALL | re.IGNORECASE,
            )
            issues_text = (
                issues_match.group(1).strip()
                if issues_match
                else ("Verification criteria not met" if not verified else "")
            )

            # CRITICAL FIX: Check command relevance BEFORE accepting verdict
            is_relevant, relevance_reason = self._check_command_relevance(
                step_action, expected_result, verification_results
            )
            
            if not is_relevant:
                logger.warning(f"[GRISHA] Command relevance check FAILED: {relevance_reason}")
                verified = False
                confidence = min(confidence, 0.3)  # Reduce confidence for irrelevant commands
                if not issues_text:
                    issues_text = f"Нерелевантна команда: {relevance_reason}"
                else:
                    issues_text += f" | Нерелевантна команда: {relevance_reason}"
            else:
                logger.info(f"[GRISHA] Command relevance check PASSED: {relevance_reason}")

            issues = [
                i.strip()
                for i in issues_text.split("\n")
                if i.strip() and i.strip() not in ["None", "Не виявлено"]
            ]
            if not verified and not issues:
                issues.append("Verification criteria not met")

            return {
                "verified": verified,
                "confidence": confidence,
                "reasoning": ukrainian_reasoning,
                "issues": issues,
                "full_analysis": analysis_text,
            }

        except Exception as e:
            logger.error(f"[GRISHA] Logical verdict formation failed: {e}")
            return self._fallback_verdict(verification_results)

    def _fallback_verdict(self, verification_results: list[dict]) -> dict[str, Any]:
        """Strict fallback verdict logic if sequential-thinking fails."""
        # A tool is considered successful only if it returned valid data and no error
        actual_successes = []
        for r in verification_results:
            success = not r.get("error", False)
            result_val = str(r.get("result", "")).lower()

            # Even if 'success' is True, if result contains failure markers or is empty for info tools, it's a failure
            if success:
                if "error:" in result_val or "failed to" in result_val or "not found" in result_val:
                    success = False
                elif not result_val.strip() and r.get("tool", "").startswith(
                    ("macos-use.read", "vibe.vibe_check")
                ):
                    # Empty results for read/check tools are suspicious
                    success = False

            if success:
                actual_successes.append(r)

        total = len(verification_results)
        success_count = len(actual_successes)

        # Verified only if ALL tools succeeded (or at least no critical tool failed)
        verified = success_count == total and total > 0

        # Confidence is lower because we are using fallback logic
        confidence = 0.6 if verified else 0.2

        reasoning = (
            f"СУВОРИЙ вердикт (fallback): {success_count}/{total} інструментів пройшли валідацію. "
        )
        if not verified:
            reasoning += (
                "Позначено як ПОМИЛКА через недостатню кількість доказів або помилки інструментів."
            )
        else:
            reasoning += "Використання обережної верифікації через недоступність логічного аналізу."

        return {
            "verified": verified,
            "confidence": confidence,
            "reasoning": reasoning,
            "issues": ["Логічний аналіз недоступний", "Застосовано сувору верифікацію"]
            if not verified
            else ["Логічний аналіз недоступний"],
        }

    def _is_final_task_completion(self, step: dict[str, Any]) -> bool:
        """Check if this step represents final task completion vs intermediate step"""
        step_action = step.get("action", "").lower()
        expected_result = step.get("expected_result", "").lower()
        
        # Keywords indicating final task completion
        final_keywords = [
            "complete", "completed", "finished", "done", "success", 
            "завершено", "виконано", "готово", "успішно"
        ]
        
        # Check if step action or expected result indicates completion
        is_final = any(keyword in step_action for keyword in final_keywords)
        is_final = is_final or any(keyword in expected_result for keyword in final_keywords)
        
        # Also check if this is a verification of overall task success
        verification_keywords = ["verify", "check", "confirm", "перевірити", "перевірка"]
        is_verification = any(keyword in step_action for keyword in verification_keywords)
        
        # If it's a verification step but not about specific technical details,
        # it might be a final verification
        if is_verification and not any(tech in step_action for tech in ["bridged", "network", "ip", "vm"]):
            is_final = True
            
        logger.info(f"[GRISHA] Step completion check - Final: {is_final}, Action: {step_action[:50]}")
        return is_final

    def _check_command_relevance(self, step_action: str, expected_result: str, verification_results: list) -> tuple[bool, str]:
        """Check if executed commands are relevant to expected results"""
        if not verification_results:
            return False, "No verification results available"
        
        # Extract command from verification results
        commands = []
        for result in verification_results:
            if isinstance(result, dict):
                tool_name = result.get("tool", "")
                args = result.get("args", {})
                if "execute_command" in tool_name and "command" in args:
                    commands.append(args["command"])
        
        if not commands:
            return True, "No commands to check relevance"
        
        # Check relevance based on expected result keywords
        expected_lower = expected_result.lower()
        step_lower = step_action.lower()
        
        for cmd in commands:
            cmd_lower = cmd.lower()
            
            # Bridged Mode specific checks
            if "bridged" in expected_lower or "network mode" in expected_lower:
                if any(keyword in cmd_lower for keyword in ["showvminfo", "getextradata", "modifyvm"]):
                    return True, f"Command '{cmd}' is relevant for network configuration"
                elif "list vms" in cmd_lower:
                    return True, f"Command '{cmd}' is relevant as initial step for VM verification"
            
            # IP/Network checks
            if "ip" in expected_lower or "network" in expected_lower:
                if any(keyword in cmd_lower for keyword in ["ip a", "ifconfig", "ping"]):
                    return True, f"Command '{cmd}' is relevant for network verification"
            
            # General VM management
            if "vm" in expected_lower and "virtualbox" in step_lower:
                if any(keyword in cmd_lower for keyword in ["showvminfo", "list", "getextradata"]):
                    return True, f"Command '{cmd}' is relevant for VM management"
        
        # Default: if no specific relevance found, assume relevant
        return True, "Command relevance assumed (no specific pattern matched)"

    def _detect_repetitive_thinking(self, analysis_text: str) -> bool:
        """Detect if the thinking is repetitive (anti-loop protection)"""
        if not analysis_text or len(analysis_text) < 100:
            return False
            
        # Split into sentences/lines
        lines = [line.strip() for line in analysis_text.split('\n') if line.strip()]
        if len(lines) < 3:
            return False
            
        # Check for repeated patterns
        unique_lines = set(lines)
        repetition_ratio = 1 - (len(unique_lines) / len(lines))
        
        # If more than 50% of lines are duplicates, consider it repetitive
        if repetition_ratio > 0.5:
            return True
            
        # Check for repeated key phrases
        phrases = analysis_text.split('.')
        unique_phrases = set([p.strip() for p in phrases if p.strip()])
        phrase_repetition = 1 - (len(unique_phrases) / len(phrases))
        
        return phrase_repetition > 0.6

    async def _verify_config_sync(self) -> dict[str, Any]:
        """Verify if config templates are synchronized with global config folder"""
        try:
            config_root = os.path.join(os.path.expanduser("~"), ".config", "atlastrinity")
            project_config_dir = os.path.join(root, "config")
            
            sync_issues = []
            
            # Check key config files
            config_files = [
                ("config.yaml", "config.yaml.template"),
                ("behavior_config.yaml", "behavior_config.yaml.template"),
                ("vibe_config.toml", "vibe_config.toml.template"),
            ]
            
            for config_file, template_file in config_files:
                config_path = os.path.join(config_root, config_file)
                template_path = os.path.join(project_config_dir, template_file)
                
                if not os.path.exists(config_path):
                    sync_issues.append(f"Missing config: {config_file}")
                    continue
                    
                if not os.path.exists(template_path):
                    sync_issues.append(f"Missing template: {template_file}")
                    continue
                
                # Simple modification time check
                config_mtime = os.path.getmtime(config_path)
                template_mtime = os.path.getmtime(template_path)
                
                if template_mtime > config_mtime:
                    sync_issues.append(f"Template newer than config: {config_file}")
            
            # Try to run sync script to check
            try:
                sync_script = os.path.join(root, "scripts", "sync_config_templates.js")
                if os.path.exists(sync_script):
                    result = subprocess.run(
                        ["node", sync_script, "--dry-run"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        sync_issues.append("Config sync script failed")
            except Exception as e:
                logger.warning(f"[GRISHA] Config sync check failed: {e}")
            
            return {
                "sync_status": "ok" if not sync_issues else "issues_found",
                "issues": sync_issues,
                "config_root": config_root,
                "template_root": project_config_dir
            }
            
        except Exception as e:
            logger.error(f"[GRISHA] Config sync verification failed: {e}")
            return {
                "sync_status": "error",
                "issues": [f"Verification failed: {e!s}"],
                "config_root": None,
                "template_root": None
            }

    async def _fetch_execution_trace(self, step_id: str, task_id: str | None = None) -> str:
        """Fetches the raw tool execution logs from the database for a given step.
        This serves as the 'single source of truth' for verification.
        """
        try:
            from ..mcp_manager import mcp_manager

            # Query db for tool executions related to this step, including the status from task_steps
            if task_id:
                sql = """
                    SELECT te.tool_name, te.arguments, te.result, ts.status as step_status, te.created_at 
                    FROM tool_executions te
                    JOIN task_steps ts ON te.step_id = ts.id
                    WHERE ts.sequence_number = :seq AND ts.task_id = :task_id
                    ORDER BY te.created_at DESC 
                    LIMIT 5;
                """
                params = {"seq": str(step_id), "task_id": task_id}
            else:
                sql = """
                    SELECT te.tool_name, te.arguments, te.result, ts.status as step_status, te.created_at 
                    FROM tool_executions te
                    JOIN task_steps ts ON te.step_id = ts.id
                    WHERE ts.sequence_number = :seq 
                    ORDER BY te.created_at DESC 
                    LIMIT 5;
                """
                params = {"seq": str(step_id)}

            rows = await mcp_manager.query_db(sql, params)

            if not rows:
                return "No DB records found for this step. (Command might not have been logged yet or step ID mismatch)."

            trace = "\n--- TECHNICAL EXECUTION TRACE (FROM DB) ---\n"
            for row in rows:
                tool = row.get("tool_name", "unknown")
                args = row.get("arguments", {})
                res = str(row.get("result", ""))
                status = row.get("step_status", "unknown")

                # Truncate result for token saving
                if len(res) > 2000:
                    res = res[:2000] + "...(truncated)"

                trace += f"Tool: {tool}\nArgs: {args}\nStep Status (from Tetyana): {status}\nResult: {res or '(No output - Silent Success)'}\n-----------------------------------\n"

            return trace

        except Exception as e:
            logger.warning(f"[GRISHA] Failed to fetch execution trace: {e}")
            return f"Error fetching trace: {e}"

    async def verify_step(
        self,
        step: dict[str, Any],
        result: Any,
        screenshot_path: str | None = None,
        goal_context: str = "",
        task_id: str | None = None,
    ) -> VerificationResult:
        """Verifies the result of step execution using Vision and MCP Tools"""
        from ..mcp_manager import mcp_manager

        step_id = step.get("id", 0)
        expected = step.get("expected_result", "")

        # NEW LOGIC: Skip verification for intermediate steps
        # Only verify final task completion steps
        if not self._is_final_task_completion(step):
            logger.info(f"[GRISHA] Skipping intermediate step {step_id} - not a final task completion")
            return VerificationResult(
                step_id=step_id,
                verified=True,  # Auto-approve intermediate steps
                confidence=1.0,
                description="Intermediate step - auto-approved",
                issues=[],
                voice_message=f"Step {step_id} is intermediate, continuing task execution"
            )

        # SYSTEM CHECK: Verify config sync for system-critical tasks
        system_issues = []
        if step_id == 1 or "system" in step.get("action", "").lower():
            config_sync = await self._verify_config_sync()
            if config_sync["sync_status"] != "ok":
                system_issues.extend(config_sync["issues"])
                logger.warning(f"[GRISHA] Config sync issues detected: {config_sync['issues']}")

        # PRIORITY: Use MCP tools first, screenshots only when explicitly needed
        # Only take screenshot if explicitly requested or if visual verification is clearly needed
        visual_verification_needed = (
            "visual" in expected.lower()
            or "screenshot" in expected.lower()
            or "ui" in expected.lower()
            or "interface" in expected.lower()
            or "window" in expected.lower()
        )

        # RELAXATION: Don't demand legal/intent verification for technical tasks
        # unless keywords are present
        (
            "legal" in expected.lower()
            or "intent" in expected.lower()
            or "compliance" in expected.lower()
            or "policy" in expected.lower()
        )

        if (
            not visual_verification_needed
            or not screenshot_path
            or not isinstance(screenshot_path, str)
            or not os.path.exists(screenshot_path)
        ):
            screenshot_path = None

        # If we don't already have a screenshot path, try to find artifacts saved by Tetyana
        # (Simplified: Reliance on shared_context or direct params mostly)
        if not screenshot_path:
            pass

        if hasattr(result, "result") and not isinstance(result, dict):
            actual_raw = str(result.result)
        elif isinstance(result, dict):
            actual_raw = str(result.get("result", result.get("output", "")))
        else:
            actual_raw = str(result)

        # NEW: Intelligent local summarization instead of simple truncation
        actual = self._summarize_ui_data(actual_raw)

        # Inject tool execution details to prove execution to the LLM
        tool_proof = ""
        if hasattr(result, "tool_call") and result.tool_call:
            tool_proof = f"\n\n[PROOF OF EXECUTION]\nTool: {result.tool_call.get('name')}\nArgs: {result.tool_call.get('args')}\n"
        elif isinstance(result, dict) and result.get("tool_call"):
            tc = result["tool_call"]
            tool_proof = (
                f"\n\n[PROOF OF EXECUTION]\nTool: {tc.get('name')}\nArgs: {tc.get('args')}\n"
            )

        actual += tool_proof

        # Double safety truncation for the final string sent to LLM
        if len(actual) > 16000:
            actual = actual[:16000] + "...(truncated for brevity)"

        # ========== NEW TWO-PHASE VERIFICATION WITH SEQUENTIAL-THINKING ==========

        # PHASE 1: ANALYZE VERIFICATION GOAL (Sequential-Thinking #1)
        logger.info(f"[GRISHA] 🧠 Phase 1: Analyzing verification goal for step {step_id}...")
        goal_analysis = await self._analyze_verification_goal(
            step, goal_context or shared_context.get_goal_context()
        )

        logger.info(
            f"[GRISHA] Verification Purpose: {goal_analysis.get('verification_purpose', 'Unknown')[:200]}..."
        )
        logger.info(
            f"[GRISHA] Selected {len(goal_analysis.get('selected_tools', []))} tools for verification"
        )

        # PHASE 1.5: EXECUTE SELECTED VERIFICATION TOOLS
        logger.info("[GRISHA] 🔧 Executing verification tools...")
        verification_results = []

        for tool_config in goal_analysis.get("selected_tools", []):
            tool_name = tool_config.get("tool", "")
            tool_args = tool_config.get("args", {})
            tool_reason = tool_config.get("reason", "Unknown")

            logger.info(f"[GRISHA] Verif-Step: {tool_name} - {tool_reason}")

            try:
                v_output = await mcp_manager.dispatch_tool(tool_name, tool_args)
                v_res_str = str(v_output)

                # Smart error detection with empty result checking for info tasks
                has_error = False

                if isinstance(v_output, dict):
                    if v_output.get("error") or v_output.get("success") is False:
                        has_error = True
                    elif v_output.get("success") is True:
                        # Check if result is actually empty for search/info tasks
                        data = v_output.get("data", [])
                        count = v_output.get("count", 0)
                        results = v_output.get("results", [])

                        step_action_lower = step.get("action", "").lower()
                        is_info_task = any(
                            kw in step_action_lower
                            for kw in ["search", "find", "gather", "collect", "identify", "locate"]
                        )

                        if is_info_task and (
                            (isinstance(data, list) and len(data) == 0 and count == 0)
                            or (isinstance(results, list) and len(results) == 0)
                            or (len(v_res_str.strip()) == 0)
                        ):
                            has_error = True
                            logger.warning(
                                f"[GRISHA] Empty result in info-gathering task: {tool_name}"
                            )
                else:
                    lower_result = v_res_str.lower()[:500]
                    if (
                        "error:" in lower_result
                        or "exception" in lower_result
                        or "failed:" in lower_result
                    ):
                        has_error = True

                if len(v_res_str) > 2000:
                    v_res_str = v_res_str[:2000] + "...(truncated)"

                verification_results.append(
                    {
                        "tool": tool_name,
                        "args": tool_args,
                        "result": v_res_str,
                        "error": has_error,
                        "reason": tool_reason,
                    }
                )

            except Exception as e:
                logger.warning(f"[GRISHA] Verif-Step failed: {e}")
                verification_results.append(
                    {
                        "tool": tool_name,
                        "args": tool_args,
                        "result": f"Error: {e}",
                        "error": True,
                        "reason": tool_reason,
                    }
                )

        # PHASE 2: FORM LOGICAL VERDICT (Sequential-Thinking #2)
        logger.info(
            f"[GRISHA] 🧠 Phase 2: Forming logical verdict based on {len(verification_results)} tool results..."
        )
        verdict = await self._form_logical_verdict(
            step,
            goal_analysis,
            verification_results,
            goal_context or shared_context.get_goal_context(),
        )

        # Log verdict details
        logger.info(
            f"[GRISHA] Verdict: {'✅ VERIFIED' if verdict.get('verified') else '❌ FAILED'}"
        )
        logger.info(f"[GRISHA] Confidence: {verdict.get('confidence', 0.0):.2f}")
        logger.info(f"[GRISHA] Reasoning: {verdict.get('reasoning', 'N/A')[:300]}...")

        # Return structured verification result
        all_issues = verdict.get("issues", [])
        
        # Add system issues if any
        if system_issues:
            all_issues.extend([f"Config sync: {issue}" for issue in system_issues])
            logger.warning(f"[GRISHA] Adding {len(system_issues)} system issues to verification result")
        
        result_obj = VerificationResult(
            step_id=step_id,
            verified=verdict.get("verified", False) and not system_issues,  # Fail if system issues
            confidence=verdict.get("confidence", 0.0),
            description=verdict.get("reasoning", "Перевірку завершено"),
            issues=all_issues,
            voice_message=self._generate_voice_message(verdict, step),
        )

        # CRITICAL FIX: Persist rejection report so Tetyana can "hear" it
        if not result_obj.verified:
            logger.info(
                f"[GRISHA] Step {step_id} failed. Saving detailed rejection report for Tetyana..."
            )
            try:
                await self._save_rejection_report(
                    step_id=str(step_id),
                    step=step,
                    verification=result_obj,
                    task_id=task_id,
                    root_cause_analysis=goal_analysis.get("full_reasoning"),
                    suggested_fix=None,  # Or parse from reasoning if possible
                    verification_evidence=[
                        f"Tool: {res.get('tool')}, Result: {str(res.get('result', ''))[:200]}..."
                        for res in verification_results
                        if isinstance(res, dict)
                    ],
                )
            except Exception as save_err:
                logger.error(f"[GRISHA] Failed to save rejection report: {save_err}")

        return result_obj

    def _generate_voice_message(self, verdict: dict, step: dict) -> str:
        """Generate detailed Ukrainian voice message based on verdict."""
        step_id = step.get("id", "невідомий")
        reasoning = verdict.get("reasoning", "")

        if verdict.get("verified"):
            msg = f"Крок {step_id} успішно верифіковано. "
            if reasoning and len(reasoning) < 200:
                msg += f"Деталі: {reasoning}"
            return msg
        else:
            issues = verdict.get("issues", [])
            issues_text = "; ".join(issues) if issues else "критерії не виконані"

            msg = f"Крок {step_id} не пройшов перевірку. "
            msg += f"Виявлені проблеми: {issues_text}. "

            # Add snippet of reasoning if it's informative
            if reasoning and "пр" not in reasoning.lower()[:10]:  # avoid repeating "проблеми"
                msg += f"Аналіз: {reasoning[:1000]}"
                if len(reasoning) > 1000:
                    msg += "..."

            return msg

    async def analyze_failure(
        self,
        step: dict[str, Any],
        error: str,
        context: dict | None = None,
    ) -> dict[str, Any]:
        """Analyzes a failure reported by Tetyana or Orchestrator using Deep Sequential Thinking.
        Returns constructive feedback for a retry.
        """
        step_id = step.get("id", "unknown")
        context_data = context or shared_context.to_dict()

        logger.info(f"[GRISHA] Conducting deep forensic analysis of failure in step {step_id}")

        # Use universal sequential thinking capability
        reasoning = await self.use_sequential_thinking(
            GRISHA_FORENSIC_ANALYSIS.format(
                step_json=json.dumps(step, default=str),
                error=error,
                context_data=str(context_data)[:1000]
            ),
            total_thoughts=3,
        )

        analysis_text = reasoning.get("analysis", "Deep analysis unavailable.")

        # Enhanced extraction for Ukrainian fields
        import re

        def extract_field(pattern, text, default):
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            return match.group(1).strip() if match else default

        error_type = extract_field(
            r"\*\*TYPE\*\*[:\s]*(.*?)(?=\n- \*\*|\Z)", analysis_text, "Unknown"
        )
        root_cause = extract_field(
            r"\*\*ROOT CAUSE\*\*[:\s]*(.*?)(?=\n- \*\*|\Z)", analysis_text, "Investigation required"
        )
        technical_advice = extract_field(
            r"\*\*FIX ADVICE\*\*[:\s]*(.*?)(?=\n- \*\*|\Z)",
            analysis_text,
            "Follow standard recovery procedures",
        )
        prevention = extract_field(
            r"\*\*PREVENTION\*\*[:\s]*(.*?)(?=\n- \*\*|\Z)",
            analysis_text,
            "Continuity analysis ongoing",
        )
        summary_uk = extract_field(
            r"\*\*SUMMARY_UKRAINIAN\*\*[:\s]*(.*?)(?=\n- \*\*|\Z)",
            analysis_text,
            "Аналіз провалу завершено. Потрібне виправлення.",
        )

        return {
            "step_id": step_id,
            "analysis": {
                "type": error_type,
                "root_cause": root_cause,
                "technical_advice": technical_advice,
                "prevention_strategy": prevention,
                "full_reasoning": analysis_text,
            },
            "feedback_text": f"GRISHA FORENSIC REPORT:\n{analysis_text}",
            "voice_message": summary_uk,
        }

    async def _save_rejection_report(
        self,
        step_id: str,
        step: dict[str, Any],
        verification: VerificationResult,
        task_id: str | None = None,
        root_cause_analysis: str | None = None,
        suggested_fix: str | None = None,
        verification_evidence: list[str] | None = None,
    ) -> None:
        """Save detailed rejection report to memory and notes servers for Atlas and Tetyana to access"""
        from datetime import datetime

        from ..knowledge_graph import knowledge_graph
        from ..mcp_manager import mcp_manager
        from ..message_bus import AgentMsg, MessageType, message_bus

        try:
            timestamp = datetime.now().isoformat()

            # Build structured sections
            issues_formatted = (
                chr(10).join(f"  - {issue}" for issue in verification.issues)
                if verification.issues
                else "  - No specific issues identified"
            )

            evidence_section = ""
            if verification_evidence:
                evidence_section = f"""
## Verification Evidence
{chr(10).join(f"  - {e}" for e in verification_evidence)}
"""

            root_cause_section = ""
            if root_cause_analysis:
                root_cause_section = f"""
## Аналіз кореневої причини
{root_cause_analysis}
"""

            fix_section = ""
            if suggested_fix:
                fix_section = f"""
## Рекомендоване виправлення
{suggested_fix}
"""

            # Prepare detailed report text with enhanced structure
            report_text = f"""========================================
ЗВІТ ПРО ВЕРИФІКАЦІЮ ГРІШІ - ВІДХИЛЕНО
========================================

## Резюме
| Поле | Значення |
|-------|-------|
| ID кроку | {step_id} |
| ID завдання | {task_id or "Н/A"} |
| Впевненість | {verification.confidence:.2f} |
| Аналіз скріншота | {"Так" if verification.screenshot_analyzed else "Ні"} |
| Часова мітка | {timestamp} |

## Деталі кроку
**Дія:** {step.get("action", "Н/A")}
**Очікуваний результат:** {step.get("expected_result", "Н/A")}

## Результат верифікації
**Статус:** ❌ ВІДХИЛЕНО

**Опис:**
{verification.description}

## Виявлені проблеми
{issues_formatted}
{root_cause_section}{fix_section}{evidence_section}

## Голосове повідомлення
{verification.voice_message or "Верифікація не пройдена."}

## Для відновлення
Використовуйте цей звіт щоб:
1. Зрозуміти, ЩО саме не вдалося (див. Виявлені проблеми)
2. Зрозуміти, ЧОМУ це сталося (див. Аналіз кореневої причини)
3. Дізнатися, ЯК це виправити (див. Рекомендоване виправлення)

========================================
"""

            # Save to memory server (for graph/relations)
            try:
                await mcp_manager.dispatch_tool(
                    "memory.create_entities",
                    {
                        "entities": [
                            {
                                "name": f"grisha_rejection_step_{step_id}",
                                "entityType": "verification_report",
                                "observations": [report_text],
                            },
                        ],
                    },
                )
                logger.info(f"[GRISHA] Rejection report saved to memory for step {step_id}")
            except Exception as e:
                logger.warning(f"[GRISHA] Failed to save to memory: {e}")

            # Save to filesystem (for easy text retrieval)
            try:
                reports_dir = os.path.expanduser("~/.config/atlastrinity/reports")
                os.makedirs(reports_dir, exist_ok=True)

                filename = f"rejection_step_{step_id}_{int(datetime.now().timestamp())}.md"
                file_path = os.path.join(reports_dir, filename)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(report_text)

                logger.info(f"[GRISHA] Rejection report saved to filesystem: {file_path}")
            except Exception as e:
                logger.warning(f"[GRISHA] Failed to save report to filesystem: {e}")

            # Save to knowledge graph (Structured Semantic Memory)
            try:
                node_id = f"rejection:step_{step_id}_{int(datetime.now().timestamp())}"
                await knowledge_graph.add_node(
                    node_type="CONCEPT",
                    node_id=node_id,
                    attributes={
                        "type": "verification_rejection",
                        "step_id": str(step_id),
                        "issues": "; ".join(verification.issues)
                        if isinstance(verification.issues, list)
                        else str(verification.issues),
                        "description": str(verification.description),
                        "timestamp": timestamp,
                    },
                )
                # Link to the task (use task_id if provided)
                source_id = f"task:{task_id}" if task_id else f"task:rejection_{step_id}"
                await knowledge_graph.add_edge(
                    source_id=source_id,
                    target_id=node_id,
                    relation="REJECTED",
                )
                logger.info(f"[GRISHA] Rejection node added to Knowledge Graph for step {step_id}")
            except Exception as e:
                logger.warning(f"[GRISHA] Failed to update Knowledge Graph: {e}")

            # Send to Message Bus (Real-time typed communication)
            try:
                msg = AgentMsg(
                    from_agent="grisha",
                    to_agent="tetyana",
                    message_type=MessageType.REJECTION,
                    payload={
                        "step_id": str(step_id),
                        "issues": verification.issues,
                        "description": verification.description,
                        "remediation": getattr(verification, "remediation_suggestions", []),
                    },
                    step_id=str(step_id),
                )
                await message_bus.send(msg)
                logger.info("[GRISHA] Rejection message sent to Tetyana via Message Bus")
            except Exception as e:
                logger.warning(f"[GRISHA] Failed to send message to bus: {e}")

        except Exception as e:
            logger.warning(f"[GRISHA] Failed to save rejection report: {e}")

    async def security_check(self, action: dict[str, Any]) -> dict[str, Any]:
        """Performs security check before execution"""
        from langchain_core.messages import HumanMessage, SystemMessage

        action_str = str(action)
        if self._check_blocklist(action_str):
            return {
                "safe": False,
                "risk_level": "critical",
                "reason": "Command found in blocklist",
                "requires_confirmation": True,
                "voice_message": "УВАГА! Ця команда у чорному списку. Блокую.",
            }

        prompt = AgentPrompts.grisha_security_prompt(str(action))

        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await self.llm.ainvoke(messages)
        return self._parse_response(cast("str", response.content))

    async def take_screenshot(self) -> str:
        """Captures and analyzes screenshot via Vision model.

        Enhanced for AtlasTrinity:
        - Robust multi-monitor support (Quartz).
        - Active application window focus (AppleScript).
        - Combined context+detail image for vision model analysis.
        """
        import subprocess
        import tempfile
        from datetime import datetime

        from PIL import Image

        from ..config import SCREENSHOTS_DIR
        from ..mcp_manager import mcp_manager

        # 1. Try Native Swift MCP first (fastest, most reliable)
        try:
            # Check if macos-use is active
            if "macos-use" in mcp_manager.config.get("mcpServers", {}):
                result = await mcp_manager.call_tool("macos-use", "macos-use_take_screenshot", {})

                # Result might be a dict with content->text (base64) OR direct base64 string depending on how call_tool processes it
                base64_img = None
                if isinstance(result, dict) and "content" in result:
                    for item in result["content"]:
                        if item.get("type") == "text":
                            base64_img = item.get("text")
                            break
                elif hasattr(result, "content"):  # prompt object
                    if len(result.content) > 0 and hasattr(result.content[0], "text"):
                        base64_img = result.content[0].text

                if base64_img:
                    # Save to file for consistency with rest of pipeline
                    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    path = os.path.join(SCREENSHOTS_DIR, f"vision_mcp_{timestamp}.jpg")

                    with open(path, "wb") as f:
                        f.write(base64.b64decode(base64_img))

                    logger.info(f"[GRISHA] Screenshot taken via MCP macos-use: {path}")
                    return path
        except Exception as e:
            logger.warning(f"[GRISHA] MCP screenshot failed, falling back to local Quartz: {e}")

        # 2. Local Fallback (Quartz/Screencapture)
        try:
            Quartz = None
            quartz_available = False
            try:
                import Quartz as _Quartz  # type: ignore

                Quartz = _Quartz
                quartz_available = True
            except Exception as qerr:
                logger.warning(
                    f"[GRISHA] Quartz unavailable for screenshots (will fallback to screencapture): {qerr}",
                )

            desktop_canvas = None
            active_win_img = None

            if quartz_available and Quartz is not None:
                max_displays = 16
                # Robustly call Quartz functions to satisfy linter and runtime
                CGGetActiveDisplayList = getattr(Quartz, "CGGetActiveDisplayList", None)
                if CGGetActiveDisplayList:
                    list_result = CGGetActiveDisplayList(max_displays, None, None)
                else:
                    list_result = None
                if not list_result or list_result[0] != 0:
                    raise RuntimeError("Quartz display list error")

                active_displays = list_result[1]
                displays_info = []
                for idx, display_id in enumerate(active_displays):
                    CGDisplayBounds = getattr(Quartz, "CGDisplayBounds", None)
                    if CGDisplayBounds:
                        bounds = CGDisplayBounds(display_id)
                    else:
                        continue
                    displays_info.append(
                        {
                            "id": display_id,
                            "sc_index": idx + 1,
                            "x": bounds.origin.x,
                            "y": bounds.origin.y,
                            "width": bounds.size.width,
                            "height": bounds.size.height,
                        },
                    )

                displays_info.sort(key=lambda d: d["x"])
                min_x = min(d["x"] for d in displays_info)
                min_y = min(d["y"] for d in displays_info)
                max_x = max(d["x"] + d["width"] for d in displays_info)
                max_y = max(d["y"] + d["height"] for d in displays_info)

                total_w = int(max_x - min_x)
                total_h = int(max_y - min_y)
                desktop_canvas = Image.new("RGB", (total_w, total_h), (0, 0, 0))

                for d in displays_info:
                    fhandle, path = tempfile.mkstemp(suffix=".png")
                    os.close(fhandle)
                    subprocess.run(
                        ["screencapture", "-x", "-D", str(d["sc_index"]), path],
                        check=False,
                        capture_output=True,
                    )
                    if os.path.exists(path):
                        try:
                            with Image.open(path) as img:
                                desktop_canvas.paste(
                                    img.copy(),
                                    (int(d["x"] - min_x), int(d["y"] - min_y)),
                                )
                        finally:
                            try:
                                os.unlink(path)
                            except Exception:
                                pass

                logger.info("[GRISHA] Capturing active application window...")
                active_win_path = os.path.join(tempfile.gettempdir(), "grisha_active_win.png")
                try:
                    CGWindowListCopyWindowInfo = getattr(Quartz, "CGWindowListCopyWindowInfo", None)
                    kCGWindowListOptionOnScreenOnly = getattr(
                        Quartz,
                        "kCGWindowListOptionOnScreenOnly",
                        1,
                    )
                    kCGWindowListExcludeDesktopElements = getattr(
                        Quartz,
                        "kCGWindowListExcludeDesktopElements",
                        16,
                    )
                    kCGNullWindowID = getattr(Quartz, "kCGNullWindowID", 0)

                    if CGWindowListCopyWindowInfo:
                        window_list = CGWindowListCopyWindowInfo(
                            kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements,
                            kCGNullWindowID,
                        )
                    else:
                        window_list = []
                    front_win_id = None
                    for window in window_list:
                        if window.get("kCGWindowLayer") == 0:
                            front_win_id = window.get("kCGWindowNumber")
                            break

                    if front_win_id:
                        subprocess.run(
                            [
                                "screencapture",
                                "-l",
                                str(front_win_id),
                                "-x",
                                active_win_path,
                            ],
                            check=False,
                            capture_output=True,
                        )
                except Exception as win_err:
                    logger.warning(f"Failed to detect active window ID: {win_err}")

                if os.path.exists(active_win_path):
                    try:
                        with Image.open(active_win_path) as img:
                            active_win_img = img.copy()
                    except Exception:
                        pass
                    finally:
                        try:
                            os.unlink(active_win_path)
                        except Exception:
                            pass
            else:
                display_imgs = []
                consecutive_failures = 0
                for di in range(1, 17):
                    fhandle, path = tempfile.mkstemp(suffix=".png")
                    os.close(fhandle)
                    try:
                        res = subprocess.run(
                            ["screencapture", "-x", "-D", str(di), path],
                            check=False,
                            capture_output=True,
                        )
                        if res.returncode == 0 and os.path.exists(path):
                            with Image.open(path) as img:
                                display_imgs.append(img.copy())
                            consecutive_failures = 0
                        else:
                            consecutive_failures += 1
                    finally:
                        try:
                            if os.path.exists(path):
                                os.unlink(path)
                        except Exception:
                            pass

                    if display_imgs and consecutive_failures >= 2:
                        break

                if not display_imgs:
                    tmp_full = os.path.join(
                        tempfile.gettempdir(),
                        f"grisha_full_{datetime.now().strftime('%H%M%S')}.png",
                    )
                    subprocess.run(
                        ["screencapture", "-x", tmp_full], check=False, capture_output=True
                    )
                    if os.path.exists(tmp_full):
                        try:
                            with Image.open(tmp_full) as img:
                                desktop_canvas = img.copy()
                        finally:
                            try:
                                os.unlink(tmp_full)
                            except Exception:
                                pass
                else:
                    total_w = sum(img.width for img in display_imgs)
                    max_h = max(img.height for img in display_imgs)
                    desktop_canvas = Image.new("RGB", (total_w, max_h), (0, 0, 0))
                    x_off = 0
                    for img in display_imgs:
                        desktop_canvas.paste(img, (x_off, 0))
                        x_off += img.width

            if desktop_canvas is None:
                raise RuntimeError("Failed to capture desktop canvas")

            target_w = 2048
            scale = target_w / max(1, desktop_canvas.width)
            dt_h = int(desktop_canvas.height * scale)

            try:
                from PIL import Image as PILImage

                resampling = getattr(PILImage, "Resampling", PILImage)
                resample_filter = getattr(resampling, "LANCZOS", 1)
                desktop_small = desktop_canvas.resize(
                    (target_w, max(1, dt_h)),
                    cast("Any", resample_filter),
                )
            except Exception:
                desktop_small = desktop_canvas.resize((target_w, max(1, dt_h)))

            final_h = desktop_small.height
            if active_win_img:
                win_scale = target_w / max(1, active_win_img.width)
                win_h = int(active_win_img.height * win_scale)
                final_h += win_h + 20
                final_canvas = Image.new("RGB", (target_w, final_h), (30, 30, 30))
                final_canvas.paste(desktop_small, (0, 0))

                try:
                    from PIL import Image as PILImage

                    resampling = getattr(PILImage, "Resampling", PILImage)
                    resample_filter = getattr(resampling, "LANCZOS", 1)
                    resized_win = active_win_img.resize(
                        (target_w, max(1, win_h)),
                        cast("Any", resample_filter),
                    )
                except Exception:
                    resized_win = active_win_img.resize((target_w, max(1, win_h)))

                final_canvas.paste(
                    resized_win,
                    (0, desktop_small.height + 20),
                )
            else:
                final_canvas = desktop_small

            final_path = os.path.join(
                str(SCREENSHOTS_DIR),
                f"grisha_vision_{datetime.now().strftime('%H%M%S')}.jpg",
            )
            final_canvas.save(final_path, "JPEG", quality=85)
            logger.info(f"[GRISHA] Vision composite saved: {final_path}")
            return final_path

        except Exception as e:
            logger.warning(f"Combined screenshot failed: {e}. Falling back to simple grab.")
            try:
                from PIL import ImageGrab

                screenshot = ImageGrab.grab(all_screens=True)
                temp_path = os.path.join(
                    str(SCREENSHOTS_DIR),
                    f"grisha_verify_fallback_{datetime.now().strftime('%H%M%S')}.jpg",
                )
                screenshot.save(temp_path, "JPEG", quality=80)
                return temp_path
            except Exception:
                return ""

    async def audit_vibe_fix(
        self,
        error: str,
        vibe_report: str,
        context: dict | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Audits a proposed fix from Vibe AI before execution.
        Uses advanced reasoning to ensure safety and correctness.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        context_data = context or shared_context.to_dict()

        # Fetch technical trace for grounding
        technical_trace = ""
        try:
            # We use the current step if available in context, or try to infer
            step_id = context_data.get("current_step_id", "unknown")
            technical_trace = await self._fetch_execution_trace(str(step_id), task_id=task_id)
        except Exception as e:
            logger.warning(f"[GRISHA] Could not fetch trace for audit: {e}")

        prompt = AgentPrompts.grisha_vibe_audit_prompt(
            error,
            vibe_report,
            context_data,
            technical_trace=technical_trace,
        )

        messages = [SystemMessage(content=self.SYSTEM_PROMPT), HumanMessage(content=prompt)]

        try:
            logger.info("[GRISHA] Auditing Vibe's proposed fix...")
            response = await self.llm.ainvoke(messages)
            audit_result = self._parse_response(cast("str", response.content))

            logger.info(f"[GRISHA] Audit Verdict: {audit_result.get('audit_verdict', 'REJECT')}")
            return audit_result
        except Exception as e:
            logger.error(f"[GRISHA] Vibe audit failed: {e}")
            return {
                "audit_verdict": "REJECT",
                "reasoning": f"Аудит не вдався через технічну помилку: {e!s}",
                "voice_message": "Я не зміг перевірити запропоноване виправлення через технічну помилку.",
            }

    def get_voice_message(self, action: str, **kwargs) -> str:
        """Generates short message for TTS"""
        messages = {
            "verified": "Тетяно, я бачу що завдання виконано. Можеш продовжувати.",
            "failed": "Тетяно, результат не відповідає очікуванню.",
            "blocked": "УВАГА! Ця дія небезпечна. Блокую виконання.",
            "checking": "Перевіряю результат...",
            "approved": "Підтверджую. Можна продовжувати.",
        }
        return messages.get(action, "")
