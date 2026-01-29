# Postmortem: Calculator Task False Positive (2026-01-28)

## Summary
Task reported 100% success (score: 1.0) but **no artifacts were created**. User requested Swift calculator compilation to DMG with installation, but only source code files were generated.

## Timeline
- **17:24** - Task started: "створити калькулятор на свіфті, скомпілював у dmg і потім встановив"
- **17:36** - Atlas evaluation: Score 1.0, "Golden Path" marked
- **17:40** - User verification: No .app, no .dmg, no installation found

## Root Causes

### 1. **GUI Simulation Instead of Real Execution** (Critical)
**Problem**: Tetyana used GUI automation tools to "simulate" compilation:
- `macos-use_open_application_and_traverse` - opened Xcode in UI
- `macos-use_click_and_traverse` - simulated clicks
- `macos-use_type_and_traverse` - typed code into editor

**What actually happened**: These tools returned `success: true` but created **zero build artifacts**.

**Database Evidence**:
```sql
SELECT sequence_number, action, tool, status FROM task_steps 
WHERE task_id = '6c26697c-89c0-480e-a084-bba46d76ccf3'
-- All 11 steps show STATUS: SUCCESS
-- But tools used: macos-use_open_application, macos-use_click, macos-use_type
-- No actual compilation commands: xcodebuild, swift build, hdiutil
```

### 2. **False Positive Evaluation System** (Critical)
**Problem**: Atlas evaluated success based on `step.get("success")` flags, not artifact existence.

**Code Location**: `src/brain/agents/atlas.py:1157-1163`
```python
for i, res in enumerate(results):
    status = "✅" if res.get("success") else "❌"  # ← Tool success ≠ Goal achievement
```

**Missing Logic**: No verification that claimed output files actually exist on disk.

### 3. **Weak Evaluation Criteria** (High)
**Problem**: Evaluation prompt asked generic questions without artifact verification requirement.

**Code Location**: `src/brain/prompts/__init__.py:516-520`
```python
CRITICAL EVALUATION:
1. Did we achieve the actual goal?  # ← Too vague
2. Was the path efficient?
3. Is this a 'Golden Path'?
```

**Missing**: "Do the claimed artifacts exist on the filesystem?"

## Fixes Implemented

### Fix #1: Artifact Verification in Atlas Evaluation
**File**: `src/brain/agents/atlas.py`

**Added**:
- `_extract_artifact_paths()` method to detect claimed output files from goal and results
- `os.path.exists()` check for each claimed artifact
- Artifact verification report injected into evaluation history
- **Override logic**: If artifacts missing, force `achieved=False` and `quality_score ≤ 0.3`

**Code**:
```python
# Extract claimed file paths (*.app, *.dmg, etc.)
claimed_artifacts = self._extract_artifact_paths(goal, results)
missing_artifacts = [a for a in claimed_artifacts if not os.path.exists(a)]

# Force failure if artifacts missing
if missing_artifacts and evaluation.get("achieved"):
    logger.warning(f"Overriding achieved=True -> False due to {len(missing_artifacts)} missing artifacts")
    evaluation["achieved"] = False
    evaluation["quality_score"] = min(evaluation.get("quality_score", 0), 0.3)
```

### Fix #2: Tetyana Tool Selection Priority
**File**: `src/brain/prompts/tetyana.py`

**Added Critical Rule**:
```
CRITICAL: COMPILATION/BUILD TASKS: For ANY compilation, building, packaging, 
or software development task (e.g., xcodebuild, swift build, npm build, make, 
cargo build, gcc, create-dmg, codesign, notarytool), you MUST use 
`execute_command` with the actual terminal command. NEVER simulate these via 
GUI clicks/typing in Xcode or other IDEs. GUI simulation does NOT create 
real build artifacts.
```

**Examples Added**:
- `execute_command(command="xcodebuild -scheme MyApp -configuration Release")`
- `execute_command(command="swift build -c release")`
- `execute_command(command="hdiutil create -volname MyApp -srcfolder ./build/MyApp.app -ov -format UDZO MyApp.dmg")`

### Fix #3: Strengthened Evaluation Prompt
**File**: `src/brain/prompts/__init__.py`

**Enhanced Rules**:
1. **ARTIFACT VERIFICATION IS MANDATORY**: Tool success (✅) does NOT equal goal achievement if artifacts are missing
2. **GUI SIMULATION IS NOT EXECUTION**: If steps show GUI clicks/typing in IDEs for compilation, goal is NOT achieved
3. Emphasis on ACTUAL achievement vs tool execution success

## Prevention Strategy

### Immediate Actions
- [x] Atlas now performs filesystem verification before marking tasks as complete
- [x] Tetyana instructed to use terminal commands for all compilation/build tasks
- [x] Evaluation criteria explicitly require artifact verification

### Long-term Improvements
1. **Pre-execution Validation**: Atlas should validate that planned steps include actual build commands (not just GUI simulation) before delegation
2. **Step Result Schema**: Enhance step results to include `artifacts_created: [path1, path2]` field
3. **Grisha Verification**: Grisha should independently verify artifact existence when reviewing build/compilation steps
4. **Tool Classification**: Mark GUI tools with `artifact_producing: false` flag in MCP registry

## Lessons Learned

1. **Trust but Verify**: Tool success flags are NOT sufficient for goal verification
2. **Simulation ≠ Execution**: GUI automation is for inspection, not for production tasks
3. **Explicit is Better**: Prompts must explicitly forbid anti-patterns (e.g., "don't use GUI for compilation")
4. **Filesystem is Truth**: For tasks claiming to create files, filesystem verification is mandatory

## Testing Recommendations

To verify fixes:
```bash
# Simulate the same task
python -c "
import asyncio
from src.brain.agents.atlas import Atlas

async def test():
    atlas = Atlas()
    
    # Simulate results with GUI tools but no artifacts
    fake_results = [
        {'step_id': '1', 'action': 'Compile app', 'success': True, 
         'result': 'xcodebuild completed', 'tool_call': {'args': {}}},
    ]
    
    goal = 'створити калькулятор на свіфті, скомпілював у dmg'
    eval_result = await atlas.evaluate_execution(goal, fake_results)
    
    # Should detect missing artifacts and return achieved=False
    assert eval_result['achieved'] == False
    assert eval_result['quality_score'] <= 0.3
    print('✅ Artifact verification working correctly')

asyncio.run(test())
"
```

## Status
**Resolved**: Fixes implemented and committed
**Risk Level**: Low (comprehensive safeguards added)
**Next Review**: After next build/compilation task

---
*Generated: 2026-01-29 01:49 UTC-08*
*Severity: Critical*
*Impact: False positive prevented future golden path contamination*
