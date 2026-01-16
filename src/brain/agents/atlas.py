"""
Atlas - The Strategist

Role: Strategic analysis, plan formulation, task delegation
Voice: Dmytro (male)
Model: GPT-4.1 / GPT-5 mini
"""

import os

# Import provider
# Robust path handling for both Dev and Production (Packaged)
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
# Check root (Dev: src/brain/agents -> root)
root_dev = os.path.join(current_dir, "..", "..", "..")
# Check resources (Prod: brain/agents -> Resources)
root_prod = os.path.join(current_dir, "..", "..")

for r in [root_dev, root_prod]:
    abs_r = os.path.abspath(r)
    if abs_r not in sys.path:
        sys.path.insert(0, abs_r)

from providers.copilot import CopilotLLM  # noqa: E402

from ..config_loader import config  # noqa: E402
from ..context import shared_context  # noqa: E402
from ..logger import logger  # noqa: E402
from ..memory import long_term_memory  # noqa: E402
from ..prompts import AgentPrompts  # noqa: E402
from ..prompts.atlas_chat import generate_atlas_chat_prompt  # noqa: E402


@dataclass
class TaskPlan:
    """Execution plan structure"""

    id: str
    goal: str
    steps: List[Dict[str, Any]]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, active, completed, failed
    context: Dict[str, Any] = field(default_factory=dict)


class Atlas:
    """
    Atlas - The Strategist

    Functions:
    - User context analysis
    - ChromaDB search (historical experience)
    - Global strategy formulation
    - Execution plan creation
    - Task delegation to Tetyana
    """

    NAME = AgentPrompts.ATLAS["NAME"]
    DISPLAY_NAME = AgentPrompts.ATLAS["DISPLAY_NAME"]
    VOICE = AgentPrompts.ATLAS["VOICE"]
    COLOR = AgentPrompts.ATLAS["COLOR"]
    SYSTEM_PROMPT = AgentPrompts.ATLAS["SYSTEM_PROMPT"]

    def __init__(self, model_name: str = "raptor-mini"):
        # Get model config (config.yaml > parameter > env variables)
        agent_config = config.get_agent_config("atlas")
        final_model = model_name
        if model_name == "raptor-mini":  # default parameter
            final_model = agent_config.get("model") or os.getenv("COPILOT_MODEL", "raptor-mini")

        self.llm = CopilotLLM(model_name=final_model)
        self.temperature = agent_config.get("temperature", 0.7)
        self.current_plan: Optional[TaskPlan] = None
        self.history: List[Dict[str, Any]] = []

    async def use_sequential_thinking(
        self, problem: str, available_tools: list = None
    ) -> Dict[str, Any]:
        """
        Use sequential-thinking MCP for deep reasoning on complex problems.
        Returns structured analysis with step-by-step recommendations.
        """
        from ..logger import logger  # noqa: E402
        from ..mcp_manager import mcp_manager  # noqa: E402

        if available_tools is None:
            available_tools = [
                "terminal",
                "filesystem",
                "browser",
                "gui",
                "applescript",
            ]

        try:
            result = await mcp_manager.call_tool(
                "sequential-thinking",
                "sequentialthinking_tools",
                {
                    "available_mcp_tools": available_tools,
                    "thought": f"Analyzing task: {problem}",
                    "thought_number": 1,
                    "total_thoughts": 5,
                    "next_thought_needed": True,
                    "current_step": {
                        "step_description": "Initial analysis",
                        "expected_outcome": "Clear understanding of the problem",
                        "recommended_tools": [],
                    },
                },
            )
            logger.info(f"[ATLAS] Sequential thinking result: {str(result)[:300]}")
            return {"success": True, "analysis": result}
        except Exception as e:
            logger.warning(f"[ATLAS] Sequential thinking unavailable: {e}")
            return {"success": False, "error": str(e)}

    async def analyze_request(
        self,
        user_request: str,
        context: Dict[str, Any] = None,
        history: List[Any] = None,
    ) -> Dict[str, Any]:
        """Analyzes user request: determines intent (chat vs task)"""
        from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

        req_lower = user_request.lower().strip()

        # No more hardcoded heuristics. The system relies on its 'brain' (LLM) to classify intent.
        # This prevents robotic, predictable responses to keywords like 'привіт'.
        
        prompt = AgentPrompts.atlas_intent_classification_prompt(
            user_request, str(context or "None"), str(history or "None")
        )
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            analysis = self._parse_response(response.content)
            
            # Ensure we have a valid intent even if the AI is vague
            if not analysis.get("intent"):
                analysis["intent"] = "chat"
            if not analysis.get("enriched_request"):
                analysis["enriched_request"] = user_request
                
            return analysis
        except Exception as e:
            logger.error(f"Intent detection LLM failed: {e}")
            return {
                "intent": "chat",
                "reason": f"System fallback due to technical issue: {e}",
                "enriched_request": user_request,
                "complexity": "low",
                "use_deep_persona": False,
                "initial_response": None # Force falling back to atlas.chat() for dynamic response
            }

    async def chat(self, user_request: str, history: List[Any] = None, use_deep_persona: bool = False) -> str:
        """
        Omni-Knowledge Chat Mode.
        Integrates Graph Memory, Vector Memory, and System Context for deep awareness.
        """
        from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

        from ..mcp_manager import mcp_manager  # noqa: E402

        # 1. Gather Context from Memory Arsenal
        graph_context = ""
        vector_context = ""
        system_status = ""
        
        # A. Graph Memory (MCP Search)
        try:
            # Search for relevant entities in the Knowledge Graph
            graph_res = await mcp_manager.call_tool(
                "memory", "search_nodes", {"query": user_request}
            )

            # Format graph result
            if isinstance(graph_res, dict) and "entities" in graph_res:
                entities = graph_res.get("entities", [])
                if entities:
                    graph_chunks = []
                    for e in entities[:3]:  # Top 3 entities
                        name = e.get("name", "Unknown")
                        obs = "; ".join(e.get("observations", [])[:2])
                        graph_chunks.append(f"Entity: {name} | Info: {obs}")
                    graph_context = "\n".join(graph_chunks)
            elif hasattr(graph_res, "content"):
                # Handle FastMCP text content
                content_list = getattr(graph_res, "content", [])
                text_content = [getattr(c, "text", "") for c in content_list if hasattr(c, "text")]
                graph_context = "\n".join(text_content)[:800]

        except Exception as e:
            logger.warning(f"[ATLAS] Chat Memory lookup failed: {e}")

        # B. Vector Memory (ChromaDB)
        try:
            if long_term_memory.available:
                # Look for similar past successful tasks/conversations
                similar_tasks = long_term_memory.recall_similar_tasks(user_request, n_results=2)
                if similar_tasks:
                    vector_context += "\nRelated Tasks:\n" + "\n".join(
                        [f"- {s['document'][:200]}..." for s in similar_tasks]
                    )

                # Look for lessons learned (errors) relevant to this topic
                similar_errors = long_term_memory.recall_similar_errors(user_request, n_results=1)
                if similar_errors:
                    vector_context += "\nRelated Lessons:\n" + "\n".join(
                        [f"- {s['document'][:200]}..." for s in similar_errors]
                    )
        except Exception as e:
            logger.warning(f"[ATLAS] Vector Memory lookup failed: {e}")

        # C. System Status
        try:
            # Snapshot of shared context
            ctx_snapshot = shared_context.to_dict()
            system_status = f"Current Project: {ctx_snapshot.get('project_root', 'Unknown')}\n"
            system_status += f"Variables: {ctx_snapshot.get('variables', {})}"
        except Exception:
            system_status = "System running."

        # D. Agent Capabilities info
        agent_capabilities = """
        - You can perform web search using `duckduckgo_search`.
        - You can read files and fetch URLs using `macos-use_fetch_url`.
        - You can search memory (KG) using `memory_search_nodes`.
        - You can check system info (calendar, notes, mail) using `macos-use` tools.
        - You can EXPLORE AND DISCOVER local code/files using `macos-use_spotlight_search`, `filesystem_list_directory`, and `filesystem_search_files`.
        - You can READ AND ANALYZE code using `filesystem_read_file`.
        """

        # 2. Generate Super Prompt
        system_prompt_text = generate_atlas_chat_prompt(
            user_query=user_request,
            graph_context=graph_context,
            vector_context=vector_context,
            system_status=system_status,
            agent_capabilities=agent_capabilities,
            use_deep_persona=use_deep_persona,
        )

        # 3. Invoke LLM
        messages = [SystemMessage(content=system_prompt_text)]

        # Add historical context (last 10 messages)
        if history:
            messages.extend(history[-10:])

        # Add current user message
        messages.append(HumanMessage(content=user_request))

        # 3. Dynamic Tool Discovery for Informational Queries
        from ..mcp_manager import mcp_manager
        
        MAX_CHAT_TURNS = 5
        current_turn = 0
        
        # Discover informational tools from ALL configured MCP servers
        available_tools_info = []
        try:
            mcp_config = mcp_manager.config.get("mcpServers", {})
            all_server_names = [name for name in mcp_config.keys() if name != "_defaults"]
            
            for server_name in all_server_names:
                # We want to list tools from ALL servers to find informational ones
                tools_list = await mcp_manager.list_tools(server_name)
                for tool in tools_list:
                    tool_name = tool.name
                    desc = tool.description.lower()
                    
                    # Pattern for "informational" tools (READ-ONLY)
                    # We are much more aggressive here to catch all discovery tools
                    is_safe = any(p in tool_name.lower() or p in desc for p in [
                        "get", "list", "read", "search", "stats", "status", "fetch", 
                        "explain", "check", "verify", "whois", "lookup", "analyze",
                        "info", "describe", "find", "show", "view", "count", "query"
                    ])
                    
                    # Exclude clearly destructive/mutative tools
                    # We must be very strict here to avoid accidental state changes in chat
                    is_mutative = any(p in tool_name.lower() or p in desc for p in [
                        "create", "delete", "write", "update", "move", "remove", "kill", "stop", "start", 
                        "exec", "run", "install", "uninstall", "post", "put", "patch", "git_commit", "git_push",
                        "set", "change", "modify", "rename", "trash", "clear"
                    ])
                    
                    if is_safe and not is_mutative:
                        # Map back to a name that includes the server for routing
                        logical_name = f"{server_name}_{tool_name}"
                        available_tools_info.append({
                            "name": logical_name,
                            "description": tool.description,
                            "input_schema": tool.inputSchema
                        })
        except Exception as e:
            logger.warning(f"[ATLAS] Dynamic tool discovery failed: {e}")
        
        # Bind discovered tools
        llm_with_tools = self.llm.bind_tools(available_tools_info)
        
        logger.info(f"[ATLAS] Starting capable chat with {len(available_tools_info)} dynamic tools for: {user_request[:50]}...")
        
        responses_with_calls = [] # To keep track of assistant messages that had tool calls
        
        while current_turn < MAX_CHAT_TURNS:
            response = await llm_with_tools.ainvoke(messages)
            
            # If model provided a direct answer without tools, we are done
            if not response.tool_calls:
                return response.content
            
            # Process Tool Calls
            for tool_call in response.tool_calls:
                logical_tool_name = tool_call.get("name")
                args = tool_call.get("args", {})
                
                # Parse logical name: {server_name}_{actual_tool_name}
                if "_" in logical_tool_name:
                    parts = logical_tool_name.split("_", 1)
                    mcp_server = parts[0]
                    mcp_tool = parts[1]
                else:
                    # Fallback if name was not properly mapped
                    mcp_server = ""
                    mcp_tool = logical_tool_name
                
                if mcp_server:
                    logger.info(f"[ATLAS CHAT] Calling dynamic tool: {mcp_server}:{mcp_tool}")
                    try:
                        # Add assistant choice to history
                        messages.append(response)
                        
                        result = await mcp_manager.call_tool(mcp_server, mcp_tool, args)
                        
                        # Format result for context
                        from langchain_core.messages import ToolMessage
                        res_str = str(result)
                        if len(res_str) > 5000: # Slightly larger limit for info
                            res_str = res_str[:5000] + "...(truncated)"
                            
                        messages.append(ToolMessage(
                            content=res_str,
                            tool_call_id=tool_call.get("id", "chat_call")
                        ))
                    except Exception as e:
                        logger.warning(f"[ATLAS CHAT] Tool execution failed: {e}")
                        messages.append(ToolMessage(
                            content=f"Error executing {mcp_server}:{mcp_tool}: {e}",
                            tool_call_id=tool_call.get("id", "chat_call")
                        ))
                else:
                    logger.warning(f"[ATLAS CHAT] Unknown tool mapping: {logical_tool_name}")
            
            current_turn += 1
            
        # Fallback to content if we exceed turns
        return response.content

    async def create_plan(self, enriched_request: Dict[str, Any]) -> TaskPlan:
        """
        Principal Architect: Creates an execution plan with Strategic Thinking.
        """
        import uuid  # noqa: E402

        from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

        task_text = enriched_request.get("enriched_request", str(enriched_request))

        # 1. STRATEGIC ANALYSIS (Internal Thought)
        # complexity = enriched_request.get("complexity", "medium") # Removed to fix F841
        logger.info(f"[ATLAS] Deep Thinking: Analyzing strategy for '{task_text[:50]}...'")

        # Memory recall for strategy
        memory_context = ""
        if long_term_memory.available:
            similar = long_term_memory.recall_similar_tasks(task_text, n_results=2)
            if similar:
                memory_context = "\nPAST LESSONS (Strategies used before):\n" + "\n".join(
                    [f"- {s['document']}" for s in similar]
                )

        simulation_prompt = AgentPrompts.atlas_simulation_prompt(task_text, memory_context)

        try:
            sim_resp = await self.llm.ainvoke(
                [
                    SystemMessage(
                        content="You are a Strategic Architect. Think technically and deeply in English."
                    ),
                    HumanMessage(content=simulation_prompt),
                ]
            )
            simulation_result = sim_resp.content if hasattr(sim_resp, "content") else str(sim_resp)
        except Exception as e:
            logger.warning(f"[ATLAS] Deep Thinking failed: {e}")
            simulation_result = "Standard execution strategy."

        # 2. PLAN FORMULATION
        use_vibe = (
            enriched_request.get("use_vibe", False)
            or enriched_request.get("intent") == "development"
        )
        vibe_directive = ""

        if use_vibe:
            vibe_directive = """
            CRITICAL DEVELOPMENT OVERRIDE:
            This is a SOFTWARE DEVELOPMENT task. You MUST delegate to 'vibe' server (Mistral AI) for:
            1. Planning architecture (vibe_smart_plan)
            2. Writing code (vibe_prompt)
            3. Debugging (vibe_analyze_error)
            
            Do NOT attempt to write complex code yourself via filesystem. Delegate to Vibe.
            """

        prompt = AgentPrompts.atlas_plan_creation_prompt(
            task_text,
            simulation_result,
            (
                shared_context.available_mcp_catalog
                if hasattr(shared_context, "available_mcp_catalog")
                else ""
            ),
            vibe_directive,
            str(shared_context.to_dict()),
        )

        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = await self.llm.ainvoke(messages)
        plan_data = self._parse_response(response.content)

        # META-PLANNING FALLBACK: If planner failed to generate steps, force reasoning
        if not plan_data.get("steps"):
            logger.info("[ATLAS] No direct steps found. Engaging Meta-Planning via sequential-thinking...")
            reasoning = await self.use_sequential_thinking(task_text)
            if reasoning.get("success"):
                # Re-try planning with reasoning context
                prompt += f"\n\nRESEARCH FINDINGS:\n{str(reasoning.get('analysis'))}"
                messages = [
                    SystemMessage(content=self.SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
                response = await self.llm.ainvoke(messages)
                plan_data = self._parse_response(response.content)

        self.current_plan = TaskPlan(
            id=str(uuid.uuid4())[:8],
            goal=plan_data.get("goal", enriched_request.get("enriched_request", "")),
            steps=plan_data.get("steps", []),
            context={**enriched_request, "simulation": simulation_result},
        )

        return self.current_plan

    async def use_sequential_thinking(self, task: str) -> Dict[str, Any]:
        """
        Engage sequential-thinking MCP server for deep reasoning and meta-planning.
        """
        from ..mcp_manager import mcp_manager  # noqa: E402
        
        logger.info(f"[ATLAS] Deep Reasoning for: {task[:50]}...")
        
        prompt = f"""You are Atlas's Reasoning Core. Analyze this task and suggest 3-5 concrete technical steps.
        TASK: {task}
        
        USE 'sequentialthinking' tool to brainstorm and provide a structured analysis.
        """
        
        try:
            # We call it twice - once for the thought, once for the analysis.
            # But the primary evidence is the thought sequence itself.
            res = await mcp_manager.call_tool(
                "sequential-thinking",
                "sequentialthinking",
                {
                    "thought": f"Initial analysis of goal: {task}",
                    "thoughtNumber": 1,
                    "totalThoughts": 3,
                    "nextThoughtNeeded": True
                }
            )
            
            # Follow up with more details
            res2 = await mcp_manager.call_tool(
                "sequential-thinking",
                "sequentialthinking",
                {
                    "thought": f"Exploring technical barriers and alternatives for {task}...",
                    "thoughtNumber": 2,
                    "totalThoughts": 3,
                    "nextThoughtNeeded": True
                }
            )
            
            # Final synthesis
            res3 = await mcp_manager.call_tool(
                "sequential-thinking",
                "sequentialthinking",
                {
                    "thought": f"Final strategy formulated for {task}.",
                    "thoughtNumber": 3,
                    "totalThoughts": 3,
                    "nextThoughtNeeded": False
                }
            )
            
            # Combine thoughts into a 'result'
            analysis = (
                f"THOUGHT 1: {res.get('content', '')}\n"
                f"THOUGHT 2: {res2.get('content', '')}\n"
                f"THOUGHT 3: {res3.get('content', '')}"
            )
            
            return {"success": True, "analysis": analysis}
        except Exception as e:
            logger.error(f"[ATLAS] Sequential thinking failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_grisha_report(self, step_id: int) -> Optional[str]:
        """Retrieve Grisha's detailed rejection report from notes or memory"""
        from ..mcp_manager import mcp_manager  # noqa: E402

        import ast  # noqa: E402
        import json  # noqa: E402

        def _parse_payload(payload: Any) -> Optional[Dict[str, Any]]:
            if isinstance(payload, dict):
                return payload
            if hasattr(payload, "structuredContent") and isinstance(
                getattr(payload, "structuredContent"), dict
            ):
                return payload.structuredContent.get("result", payload.structuredContent)
            if hasattr(payload, "content"):
                for item in getattr(payload, "content", []) or []:
                    text = getattr(item, "text", None)
                    if isinstance(text, dict):
                        return text
                    if isinstance(text, str):
                        try:
                            return json.loads(text)
                        except Exception:
                            try:
                                return ast.literal_eval(text)
                            except Exception:
                                continue
            return None

        # Try notes first (faster and cleaner)
        try:
            result = await mcp_manager.call_tool(
                "notes",
                "search_notes",
                {
                    "category": "verification_report",
                    "tags": [f"step_{step_id}"],
                    "limit": 1,
                },
            )
            data = _parse_payload(result)
            if data and data.get("notes"):
                notes = data.get("notes") or []
                if notes:
                    note_id = notes[0].get("id")
                    if note_id:
                        note_result = await mcp_manager.call_tool(
                            "notes", "read_note", {"note_id": note_id}
                        )
                        note_data = _parse_payload(note_result)
                        if note_data and note_data.get("content"):
                            logger.info(
                                f"[ATLAS] Retrieved Grisha's report from notes for step {step_id}"
                            )
                            return note_data.get("content", "")
        except Exception as e:
            logger.warning(f"[ATLAS] Could not retrieve from notes: {e}")

        # Fallback to memory
        try:
            result = await mcp_manager.call_tool(
                "memory", "search_nodes", {"query": f"grisha_rejection_step_{step_id}"}
            )

            if result and hasattr(result, "content"):
                for item in result.content:
                    if hasattr(item, "text"):
                        return item.text
            elif isinstance(result, dict) and "entities" in result:
                entities = result["entities"]
                if entities and len(entities) > 0:
                    return entities[0].get("observations", [""])[0]

            logger.info(f"[ATLAS] Retrieved Grisha's report from memory for step {step_id}")
        except Exception as e:
            logger.warning(f"[ATLAS] Could not retrieve from memory: {e}")

        return None

    async def help_tetyana(self, step_id: int, error: str) -> Dict[str, Any]:
        """Helps Tetyana when she is stuck, using shared context and Grisha's feedback for better solutions"""
        from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

        # Get context for better recovery suggestions
        context_info = shared_context.to_dict()

        # Try to get Grisha's detailed report
        grisha_report = await self.get_grisha_report(step_id)
        grisha_feedback = ""
        if grisha_report:
            grisha_feedback = f"\n\nGRISHA'S DETAILED FEEDBACK:\n{grisha_report}\n"

        prompt = AgentPrompts.atlas_help_tetyana_prompt(
            step_id,
            error,
            grisha_feedback,
            context_info,
            self.current_plan.steps if self.current_plan else [],
        )

        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        logger.info(f"[ATLAS] Helping Tetyana with context: {context_info}")
        response = await self.llm.ainvoke(messages)
        return self._parse_response(response.content)

    async def evaluate_execution(self, goal: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Atlas reviews the execution results of Tetyana and Grisha.
        Determines if the goal was REALLY achieved and if the strategy is worth remembering.
        """
        from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

        # Prepare execution summary for LLM
        history = ""
        for i, res in enumerate(results):
            status = "✅" if res.get("success") else "❌"
            history += f"{i + 1}. [{res.get('step_id')}] {res.get('action')}: {status} {str(res.get('result'))[:200]}\n"
            if res.get("error"):
                history += f"   Error: {res.get('error')}\n"

        prompt = AgentPrompts.atlas_evaluation_prompt(goal, history)

        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        logger.info(f"[ATLAS] Evaluating execution quality for goal: {goal[:50]}...")
        try:
            response = await self.llm.ainvoke(messages)
            evaluation = self._parse_response(response.content)
            logger.info(f"[ATLAS] Evaluation complete. Score: {evaluation.get('quality_score', 0)}")
            return evaluation
        except Exception as e:
            logger.error(f"[ATLAS] Evaluation failed: {e}")
            return {"quality_score": 0, "achieved": False, "should_remember": False}

    def get_voice_message(self, action: str, **kwargs) -> str:
        """
        Generates dynamic TTS message.
        """
        if action == "plan_created":
            count = kwargs.get("steps", 0)
            suffix = "кроків"
            if count == 1:
                suffix = "крок"
            elif 2 <= count <= 4:
                suffix = "кроки"
            return f"План готовий. {count} {suffix}. Тетяно, виконуй."

        elif action == "no_steps":
            return "Не бачу необхідних кроків для виконання цього запиту."

        elif action == "enriched":
            return "Контекст проаналізовано. Розширюю запит."

        elif action == "helping":
            return "Бачу проблему. Пробую альтернативний підхід."

        elif action == "delegating":
            return "Тетяно, передаю керування тобі."

        elif action == "recovery_started":
            return f"Крок {kwargs.get('step_id', '?')} зупинився. Шукаю рішення."

        elif action == "vibe_engaged":
            return (
                f"Залучаю Vibe для глибинного аналізу помилки у кроці {kwargs.get('step_id', '?')}."
            )

        return f"Атлас: {action}"

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON response from LLM"""
        import json  # noqa: E402

        try:
            # Find JSON in response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass
        return {"raw": content}
