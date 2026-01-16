from ..config import WORKSPACE_DIR
from .atlas import ATLAS
from .common import DEFAULT_REALM_CATALOG  # re-export default catalog
from .grisha import GRISHA
from .tetyana import TETYANA

__all__ = ["DEFAULT_REALM_CATALOG", "ATLAS", "TETYANA", "GRISHA", "AgentPrompts"]


class AgentPrompts:
    """Compatibility wrapper that exposes the same interface while sourcing prompts from modular files"""

    ATLAS = ATLAS
    TETYANA = TETYANA
    GRISHA = GRISHA

    @staticmethod
    def tetyana_reasoning_prompt(
        step: str,
        context: dict,
        tools_summary: str = "",
        feedback: str = "",
        previous_results: list = None,
        global_goal: str = "",
        parent_action: str = "",
    ) -> str:
        feedback_section = (
            f"\n        PREVIOUS REJECTION FEEDBACK (from Grisha):\n        {feedback}\n"
            if feedback
            else ""
        )

        results_section = ""
        if previous_results:
            # Format results nicely
            formatted_results = []
            for res in previous_results:
                # Truncate long outputs
                res_str = str(res)
                if len(res_str) > 1000:
                    res_str = res_str[:1000] + "...(truncated)"
                formatted_results.append(res_str)
            results_section = f"\n        RESULTS OF PREVIOUS STEPS (Use this data to fill arguments):\n        {formatted_results}\n"

        goal_section = f"\n        GLOBAL GOAL: {global_goal}\n" if global_goal else ""
        parent_section = f"\n        INTERMEDIATE GOAL (Context of parent step): {parent_action}\n" if parent_action else ""

        return f"""Analyze how to execute this atomic step: {step}.
        {goal_section}
        {parent_section}
        CONTEXT: {context}
        {results_section}
        {feedback_section}
        {tools_summary}

        Your task is to choose the BEST tool and arguments.
        CRITICAL: Follow the 'Schema' provided for each tool EXACTLY. Ensure parameter names and types match.
        If there is feedback from Grisha above, ADAPT your strategy to address his concerns.

        Respond in JSON:
        {{
            "thought": "Internal technical analysis in ENGLISH (Which tool? Which args? Why based on schema?)",
            "proposed_action": {{ "tool": "name", "args": {{...}} }},
            "voice_message": "Ukrainian message for the user describing the action"
        }}
        """

    @staticmethod
    def tetyana_reflexion_prompt(
        step: str, error: str, history: list, tools_summary: str = ""
    ) -> str:
        return f"""Analysis of Failure: {error}.

        Step: {step}
        History of attempts: {history}
        {tools_summary}

        Determine if you can fix this by changing the TOOL or ARGUMENTS for THIS step.
        If the failure is logical or requires changing the goal, set "requires_atlas": true.

        Respond in JSON:
        {{
            "analysis": "Technical cause of failure (English)",
            "fix_attempt": {{ "tool": "name", "args": {{...}} }},
            "requires_atlas": true/false,
            "voice_message": "Ukrainian explanation of why it failed and how you are fixing it"
        }}
        """

    @staticmethod
    def tetyana_execution_prompt(step: str, context_results: list) -> str:
        return f"""Execute this task step: {step}.
    Current context results: {context_results}
    Respond ONLY with JSON:
    {{
        "analysis": "Ukrainian explanation",
        "tool_call": {{ "name": "...", "args": {{...}} }},
        "voice_message": "Ukrainian message for user"
    }}
    """

    @staticmethod
    def grisha_strategy_prompt(
        step_action: str, expected_result: str, context: dict, overall_goal: str = ""
    ) -> str:
        return f"""You are the Verification Strategist.

        OVERALL GOAL: {overall_goal}
        Step: {step_action}
        Expected Result: {expected_result}

        Create a verification strategy:
        1. VISION: Use 'macos-use_take_screenshot' for UI layout.
        2. OCR/TEXT: Use 'macos-use_analyze_screen' for text on screen.
        3. UI TREE: Use 'macos-use_refresh_traversal' for structured accessibility verification.
        4. SYSTEM: Use MCP tools (filesystem, terminal) for system data.
        
        Prefer native 'macos-use' tools for macOS interface checks.

        Strategy:
        """

    @staticmethod
    def grisha_verification_prompt(
        strategy_context: str,
        step_id: int,
        step_action: str,
        expected: str,
        actual: str,
        context_info: dict,
        history: list,
        overall_goal: str = "",
        tetyana_thought: str = "",
    ) -> str:
        return f"""Verify the result of the following step using MCP tools FIRST, screenshots only when necessary.

    OVERALL GOAL: {overall_goal}
    STRATEGIC GUIDANCE (Follow this!):
    {strategy_context}

    Step {step_id}: {step_action}
    Expected Result: {expected}
    Actual Output/Result: {actual}
    
    TETYANA'S INTENT (Monologue from execution):
    {tetyana_thought or "No thought documented."}

    Shared Context (for correct paths and global situation): {context_info}

    Verification History (Tool actions taken during this verification): {history}

    PRIORITY ORDER FOR VERIFICATION:
    1. Use MCP tools to verify results (filesystem, terminal, git, etc.)
    2. Check files, directories, command outputs directly
    3. ONLY use screenshots for visual/UI verification when explicitly needed

    Analyze the current situation. If you can verify using MCP tools, do that first.
    Use 'macos-use_take_screenshot' for visual UI verification.
    Use 'macos-use_analyze_screen' for screen text (OCR) analysis.
    
    TRUST THE TOOLS:
    - If an MCP tool returns a success result (process ID, file content, search results), ACCEPT IT.
    - REASONING TOOLS: If 'sequential-thinking' or 'vibe_ask' provides a thought process or analysis, TRUST IT as proof of execution for logic-based steps.
    - Do NOT reject technical success just because you didn't see it visually on a screenshot.
    - If the goal was to kill a process and 'pgrep' returns nothing, that is SUCCESS.

    Respond STRICTLY in JSON.
    
    Example SUCCESS response:
    {{
      "action": "verdict",
      "verified": true,
      "confidence": 1.0,
      "description": "Terminal output confirms file was created successfully.",
      "voice_message": "Завдання виконано."
    }}

    Example REJECTION response:
    {{
      "action": "verdict",
      "verified": false,
      "confidence": 0.8,
      "description": "Expected to find directory 'mac-discovery' with specific structure, but directory does not exist.",
      "issues": ["Directory 'mac-discovery' not found"],
      "voice_message": "Результат не прийнято. Директорія не створена.",
      "remediation_suggestions": ["Create mac-discovery directory"]
    }}"""

    # --- ATLAS PROMPTS ---

    @staticmethod
    def atlas_intent_classification_prompt(user_request: str, context: str, history: str) -> str:
        return f"""Analyze the user request and decide if it's a simple conversation, a technical task, or a SOFTWARE DEVELOPMENT task.

User Request: {user_request}
Context: {context}
Conversation History: {history}

CRITICAL CLASSIFICATION RULES:
1. 'chat' - Greetings, 'How are you', jokes, appreciation (thanks), or SIMPLE CONFIRMATIONS.
2. 'task' - Direct instructions to DO something (open app, run command, search file).
3. 'development' - Requests to CREATE, BUILD, or WRITE software, code, scripts, apps, websites, APIs.
   Examples: "Create a Python script", "Build a website", "Write an API", "Develop a bot"

If request is 'development', set complexity to 'high' and use_vibe to true.

ALL textual responses (reason) MUST be in UKRAINIAN.

Respond STRICTLY in JSON:
{{
    "intent": "chat" or "task" or "development",
    "reason": "Explain your choice in Ukrainian",
    "enriched_request": "Detailed description of the request (English)",
    "complexity": "low/medium/high",
    "use_vibe": true/false (true for development tasks)
}}
"""

    @staticmethod
    def atlas_chat_prompt() -> str:
        return """You are in friendly conversation mode.
Your role: Witty, smart interlocutor Atlas.
Style: Concise, with humor.
LANGUAGE: You MUST respond in UKRAINIAN only!
Do not suggest creating a plan, just talk."""

    @staticmethod
    def atlas_simulation_prompt(task_text: str, memory_context: str) -> str:
        return f"""Think deeply as a Strategic Architect about: {task_text}
        {memory_context}

        Analyze:
        1. Underlying logic of the task.
        2. Sequence of apps/tools needed.
        3. Potential technical barriers on macOS.

        Respond in English with a technical strategy.
        """

    @staticmethod
    def atlas_plan_creation_prompt(
        task_text: str,
        strategy: str,
        catalog: str,
        vibe_directive: str = "",
        context: str = "",
    ) -> str:
        context_section = f"\n        ENVIRONMENT & PATHS:\n        {context}\n" if context else ""
        
        return f"""Create a Master Execution Plan.

        REQUEST: {task_text}
        STRATEGY: {strategy}
        {context_section}
        {vibe_directive}
        {catalog}

        CONSTRAINTS:
        - Output JSON matching the format in your SYSTEM PROMPT.
        - 'goal', 'reason', and 'action' descriptions MUST be in English (technical precision).
        - 'voice_summary' MUST be in UKRAINIAN (for the user).
        - **META-PLANNING AUTHORIZED**: If the task is complex, you MAY include reasoning steps (using `sequential-thinking`) to discover the path forward. Do not just say "no steps found". Goal achievement is mandatory.

        Steps should be atomic and logical.
        """

    @staticmethod
    def atlas_help_tetyana_prompt(
        step_id: int,
        error: str,
        grisha_feedback: str,
        context_info: dict,
        current_plan: list,
    ) -> str:
        return f"""Tetyana is stuck at step {step_id}.

 Error: {error}
 {grisha_feedback}

 SHARED CONTEXT: {context_info}

 Current plan: {current_plan}

 You are the Meta-Planner. Provide an ALTERNATIVE strategy or a structural correction.
 IMPORTANT: If Grisha provided detailed feedback above, use it to understand EXACTLY what went wrong and avoid repeating the same mistake.

 Output JSON matching the 'help_tetyana' schema:
 {{
     "reason": "English analysis of the failure (incorporate Grisha's feedback if available)",
     "alternative_steps": [
         {{"id": 1, "action": "English description", "expected_result": "English description"}}
     ],
     "voice_message": "Short Ukrainian message explaining the pivot to the user"
 }}
 """

    @staticmethod
    def atlas_evaluation_prompt(goal: str, history: str) -> str:
        return f"""Review the execution of the following task.

        GOAL: {goal}

        EXECUTION HISTORY:
        {history}

        CRITICAL EVALUATION:
        1. Did we achieve the actual goal?
        2. Was the path efficient?
        3. Is this a 'Golden Path' that should be a lesson for the future?

        Respond STRICTLY in JSON:
        {{
            "quality_score": 0.0 to 1.0 (float),
            "achieved": true/false,
            "analysis": "Critique in UKRAINIAN",
            "compressed_strategy": [
                "Step 1 intent",
                "Step 2 intent",
                ...
            ],
            "should_remember": true/false
        }}
        """

    # --- GRISHA PROMPTS ---

    @staticmethod
    def grisha_security_prompt(action_str: str) -> str:
        return f"""Analyze this action for security risks: {action_str}

        Risks to check:
        1. Data loss (deletion, overwrite)
        2. System damage (system files, configs)
        3. Privacy leaks (uploading keys, passwords)

        Respond in JSON:
        {{
            "safe": true/false,
            "risk_level": "low/medium/high/critical",
            "reason": "English technical explanation",
            "requires_confirmation": true/false,
            "voice_message": "Ukrainian warning if risky, else empty"
        }}
        """

    @staticmethod
    def grisha_strategist_system_prompt(decision_context: str) -> str:
        return f"""You are a Verification Strategist. Consider the environment and choose the best verification stack.
        ENVIRONMENT_DECISION: {decision_context}
        When visual evidence is conclusive, prioritize Vision verification. When authoritative system/data checks are needed, prefer MCP servers (favor local Swift-based MCP servers when available). Output internal strategies in English."""
