# Scripts Directory Analysis & Cleanup Plan

## Current State Analysis

### 📁 Scripts in `scripts/` directory:

#### ✅ **ACTIVE - Used by package.json or system**

1. **sync_config_templates.js** - Used by `npm run config:sync`
   - **Status**: KEEP - активно використовується
   - **Action**: None

2. **build_mac_custom.sh** - Used by `npm run build:mac:custom`
   - **Status**: KEEP - build script
   - **Action**: None

3. **fresh_install.sh** - Used by `npm run fresh-install`
   - **Status**: KEEP - setup script
   - **Action**: None

4. **clean-cache.sh** - Used by `npm run clean`
   - **Status**: KEEP - maintenance
   - **Action**: None

5. **setup.sh** - Wrapper for setup_dev.py
   - **Status**: KEEP - entry point
   - **Action**: None

#### ⚠️ **UTILITY - Development/Testing Scripts**

6. **clean_full.sh** - Full cleanup utility
   - **Status**: REVIEW - possibly redundant with clean-cache.sh
   - **Action**: Check if different from clean-cache.sh

7. **final_verification.sh** - Verification script
   - **Status**: MOVE to `src/maintenance/`
   - **Reason**: Maintenance utility

8. **live_vibe_monitor.sh** - Vibe monitoring
   - **Status**: MOVE to `src/maintenance/`
   - **Reason**: Development utility

9. **monitor_vibe.sh** - Vibe monitoring
   - **Status**: MOVE to `src/maintenance/` or DELETE if duplicate
   - **Reason**: Possibly duplicate of live_vibe_monitor.sh

10. **restart_brain.sh** - Brain restart utility
    - **Status**: KEEP or MOVE to `src/maintenance/`
    - **Reason**: Useful dev utility

11. **restart_vibe_clean.sh** - Vibe restart
    - **Status**: MOVE to `src/maintenance/`
    - **Reason**: Development utility

12. **setup_test_env.sh** - Test environment setup
    - **Status**: MOVE to `src/testing/`
    - **Reason**: Testing utility

13. **sync_secrets.sh** - GitHub secrets sync
    - **Status**: KEEP - DevOps utility
    - **Action**: None

14. **test_bridge_interaction.cjs** - Bridge testing
    - **Status**: MOVE to `src/testing/`
    - **Reason**: Test script

15. **test_vibe_streaming.sh** - Vibe stream testing
    - **Status**: MOVE to `src/testing/`
    - **Reason**: Test script

16. **verify_fixes.sh** - Fix verification
    - **Status**: MOVE to `src/maintenance/`
    - **Reason**: Maintenance utility

#### ❌ **OBSOLETE - Should be deleted**

17. **graph_preview.mmd** - Mermaid diagram
    - **Status**: DELETE or MOVE to `docs/`
    - **Reason**: Documentation artifact

18. **tools_output.txt** - Output file (empty)
    - **Status**: DELETE
    - **Reason**: Temporary file

19. **verify_graph_mcp.txt** - Large text file (32KB)
    - **Status**: DELETE or MOVE to `docs/` if needed
    - **Reason**: Looks like output/log file

20. ****init**.py** - Empty Python init
    - **Status**: DELETE
    - **Reason**: Scripts shouldn't be a Python package

## Recommended Actions

### Phase 1: Cleanup Obsolete Files

```bash
# Delete temporary/obsolete files
rm scripts/__init__.py
rm scripts/tools_output.txt
rm scripts/verify_graph_mcp.txt

# Move documentation if needed
mv scripts/graph_preview.mmd docs/ # if useful, otherwise delete
```

### Phase 2: Reorganize Testing Scripts

```bash
# Move test scripts to src/testing/
mv scripts/test_bridge_interaction.cjs src/testing/
mv scripts/test_vibe_streaming.sh src/testing/
mv scripts/setup_test_env.sh src/testing/
```

### Phase 3: Reorganize Maintenance Scripts

```bash
# Move maintenance scripts to src/maintenance/
mv scripts/final_verification.sh src/maintenance/
mv scripts/live_vibe_monitor.sh src/maintenance/
mv scripts/monitor_vibe.sh src/maintenance/ # or delete if duplicate
mv scripts/restart_brain.sh src/maintenance/
mv scripts/restart_vibe_clean.sh src/maintenance/
mv scripts/verify_fixes.sh src/maintenance/
```

### Phase 4: Review Duplicates

- Compare `clean-cache.sh` vs `clean_full.sh`
- Compare `monitor_vibe.sh` vs `live_vibe_monitor.sh`
- Delete duplicates

### Phase 5: Final scripts/ Structure

After cleanup, `scripts/` should only contain:

```
scripts/
├── build_mac_custom.sh       # Build utilities
├── clean-cache.sh            # Cleanup utilities
├── fresh_install.sh          # Setup utilities
├── setup.sh                  # Setup wrapper
├── sync_config_templates.js  # Config management
└── sync_secrets.sh           # DevOps utilities
```

## Benefits

1. ✅ **Clear separation**: Build/setup vs testing vs maintenance
2. ✅ **Better organization**: Related scripts grouped together
3. ✅ **Easier to find**: Logical structure
4. ✅ **Less confusion**: No duplicate or obsolete files
5. ✅ **Proper Python imports**: Testing/maintenance scripts can import from src/

## Notes

- Scripts that stay in `scripts/` are those used by npm/build system
- Testing scripts belong in `src/testing/`
- Maintenance/dev utilities belong in `src/maintenance/`
- This aligns with the project structure and makes imports cleaner
