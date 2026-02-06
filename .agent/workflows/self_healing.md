---
description: Formal Self-Healing Workflow with Sandbox Verification and State Preservation
---

# Self-Healing Protocol (The "Phoenix" Protocol)

This workflow defines the standard procedure for handling **Critical Logic Errors** and **System State Corruption**. It ensures that fixes are analyzed, tested in isolation, and applied without losing task progress.

## 1. Deep Analysis Phase (The Diagnosis)

**Trigger**: `ErrorRouter` classifies error as `LOGIC` or `STATE`.

1.  **Stop Execution**: Pause the current task loop.
2.  **Sequential Thinking**: The Agent (Vibe/Atlas) MUST perform a root cause analysis using `sequential-thinking` MCP tool.
    - _Constraint_: Do not propose a fix until the root cause is confirmed by log evidence or reproduction.
3.  **Reproduction**: Create a minimal reproduction script (e.g., `tests/reproduce_issue_X.py`) if feasible.

## 2. Sandbox Verification Phase (The Lab)

**Goal**: Verify the fix without breaking the main repository.

1.  **Isolate**:
    - Identify the target file (e.g., `src/module/broken.py`).
    - Copy it to a sandbox location (e.g., `/tmp/sandbox/broken.py` or `tests/sandbox/`).
2.  **Apply Fix**:
    - Apply the proposed code changes to the **Sandboxed File**.
3.  **Verify**:
    - Run the reproduction script against the sandboxed file.
    - _Condition_: If verification fails -> Return to **Analysis Phase**.
    - _Condition_: If verification passes -> Proceed to **Integration Phase**.

    _Note_: Use `src.brain.tools.sandbox_runner` if available to automate this.

## 3. Integration Phase (The Surgery)

1.  **Apply Patch**: Apply the verified fix to the actual repository file.
2.  **Lint/Check**: Run quick linting/integrity checks (`npm run lint` or `bandit`).

## 4. Resilience Phase (The Phoenix Rebirth)

**Goal**: Restart the process to clear any memory corruption, while preserving task state.

1.  **Snapshot State**:
    - Call `save_recovery_state` tool (or `Orchestrator.save_recovery_snapshot`).
    - This saves:
      - Current Task Step ID.
      - Full Conversation History.
      - Active `state_manager` (Redis) keys.
      - Pending inputs/outputs.
2.  **Restart**:
    - Execute system restart (e.g., `sys.exit(0)` if managed by a supervisor, or specific restart command).
3.  **Resume**:
    - On boot, `Orchestrator` detects `.recovery_state.json`.
    - Loads state.
    - Resumes execution from the exact step where it paused.

// turbo

## 5. Post-Recovery Verification

1.  **Verify Stability**: Ensure the error does not recur within the next 2 steps.
