# Pyrefly Import Resolution Issue

## Problem

Pyrefly (v0.52.0) has a known issue with resolving `src.brain.*` module imports in this project. The error manifests as:

```
ERROR Cannot find module `src.brain.config.config_loader` [missing-import]
```

## Root Cause

The issue appears to be related to pyrefly's import resolution mechanism when dealing with:
1. The `src.` prefix in imports
2. Complex module structure with backward compatibility shims
3. The way pyrefly infers the import root from project layout

## Current Status

- **Pyrefly**: Disabled in lefthook.yml (07-pyrefly)
- **Pyright**: Working correctly and provides comprehensive type checking
- **Ruff**: Working correctly for linting and formatting
- **All other linters**: Working correctly

## Workarounds Attempted

1. ✅ **Fixed pyproject.toml configuration** - Removed invalid `search_paths` key
2. ❌ **PYTHONPATH manipulation** - Did not resolve the issue
3. ❌ **Alternative pyrefly.toml configuration** - Not supported keys
4. ❌ **Running from different directories** - Same issue persists
5. ✅ **Current solution**: Disabled pyrefly with informative message

## Solutions for Future

### Option 1: Upgrade Pyrefly
Check if newer versions of pyrefly fix the import resolution issue:
```bash
.venv/bin/pip install --upgrade pyrefly
```

### Option 2: Fix Import Structure
Consider modifying the import structure to be more pyrefly-friendly:
- Remove `src.` prefix from imports
- Simplify module structure
- Remove backward compatibility shims

### Option 3: Alternative Configuration
Research pyrefly documentation for proper configuration of complex projects.

### Option 4: Replace Pyrefly
Consider replacing pyrefly with an alternative type checker that works better with the project structure.

## Testing Pyrefly Fixes

To test if pyrefly is working:
```bash
# Test single file
.venv/bin/python -m pyrefly check src/providers/factory.py

# Test full project
.venv/bin/python -m pyrefly check src

# If working, re-enable in lefthook.yml:
# 07-pyrefly:
#   run: .venv/bin/python -m pyrefly check src
```

## Impact

- **Minimal**: Pyright provides comprehensive type checking
- **No functional impact**: Code quality and type safety are maintained
- **CI/CD**: All other linting tools continue to work normally

## Last Updated

2026-02-12 - Issue identified and pyrefly temporarily disabled
