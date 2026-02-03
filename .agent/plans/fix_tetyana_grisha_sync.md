# Implementation Plan - Fixing Tetyana and Grisha Verification Sync

## Problem Statement

The user reported that either Tetyana or Grisha is performing incorrect actions.
Analysis reveals several issues:

1.  **Feedback Sync Gap**: Tetyana fails to retrieve Grisha's detailed rejection feedback from memory because the Memory MCP server returns `results` while Tetyana expects `entities` or `content`.
2.  **Vibe Session Persistence**: Vibe's `vibe_prompt` always uses `--resume`, which fails if the session doesn't already exist (e.g., first run of a constraint check).
3.  **Ambiguous Logging**: Tetyana's logs state she is fetching from memory when she is actually trying notes first.

## Proposed Changes

### 1. `src/brain/agents/tetyana.py`

- Fix `_fetch_feedback_from_memory` to correctly handle the `results` key returned by the Memory MCP server.
- Update the log message in `_fetch_grisha_feedback` to be more accurate (e.g., "fetching feedback from sync sources").

### 2. `src/mcp_server/vibe_server.py`

- Update `vibe_prompt` to check if the session directory exists before adding the `--resume` flag.
- Add error handling for "Session not found" to fallback to a fresh run.

### 3. `src/mcp_server/vibe_config.py`

- Update `VibeConfig.to_cli_args` to make `--resume` optional/conditional based on a new flag or automatic detection. (Actually, better to handle it in `vibe_server.py` calling logic).

## Verification Plan

1.  Verify Tetyana correctly fetches feedback from memory after a simulated Grisha rejection.
2.  Verify Vibe constraint checks succeed even on the first run (no "Session not found" error).
3.  Check logs for clear step-by-step reporting.
