
        technical_section = ""
        if technical_trace:
             technical_section = f"""
    TECHNICAL EXECUTION LOG (TRUTH SOURCE - FROM DATABASE):
    This log shows exactly what tool was executed and what the result was. 
    TRUST THIS LOG over visual inspection if there is a conflict.
    {technical_trace}
    """

        return f"""Verify the result of the following step using MCP tools FIRST, screenshots only when necessary.

    OVERALL CONTEXT:
    {goal_context}
    
    STRATEGIC GUIDANCE (Follow this!):
    {strategy_context}

    Step {step_id}: {step_action}
    Expected Result: {expected}
    Actual Output/Result: {actual}
    
    TETYANA'S INTENT (Monologue from execution):
    {tetyana_thought or "No thought documented."}

    Shared Context (for correct paths and global situation): {context_info}
    
    {technical_section}

    DATABASE AUDIT (Authority):
    If Tetyana's report is ambiguous or if this step is critical, you MUST use 'query_db' tool to see exactly what happened in the background.
    - Check 'tool_executions' for the exact command, arguments, and full untruncated result of Tetyana's tool calls.
    - Example: SELECT * FROM tool_executions WHERE step_id = '{step_id}' ORDER BY created_at DESC;

    Verification History (Tool actions taken during this verification): {history}

    PRIORITY ORDER FOR VERIFICATION:
    1. Use MCP tools to verify results (filesystem, terminal, git, etc.)
    2. Check files, directories, command outputs directly
    3. ONLY use screenshots for visual/UI verification when explicitly needed

    Analyze the current situation. If you can verify using MCP tools, do that first.
    Use 'macos-use_take_screenshot' for visual UI verification.
    Use 'macos-use_analyze_screen' for screen text (OCR) analysis.
    
    CRITICAL VERIFICATION RULE:
    - You are verifying STEP {step_id}: "{step_action}".
    - If the "Actual Output" or Tool Results prove that THIS step's "Expected Result" is met, then VERIFIED=TRUE.
    - RECURSIVE VERIFICATION: If the step involves creating folders inside other folders (e.g., 'Images/2025-07'), you MUST use 'ls -R' or 'find' to verify the deep structure, not just a simple 'ls'.
    - Do NOT reject the result because the overall task/goal is not yet finished. You are only auditor for this atomic step.

    TRUST THE TOOLS:
    - If an MCP tool returns a success result (process ID, file content, search results), ACCEPT IT.
    - REASONING TOOLS: If 'sequential-thinking' or 'vibe_ask' provides a thought process or analysis, TRUST IT as proof of execution for logic-based steps.
    - Do NOT reject technical success just because you didn't see it visually on a screenshot.
    - If the goal was to kill a process and 'pgrep' returns nothing, that is SUCCESS.
    - If the TECHNICAL EXECUTION LOG above shows success (exit code 0, file created, etc.), TRUST IT overrides any visual ambiguity.

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
