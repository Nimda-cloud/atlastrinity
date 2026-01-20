---
description: Perform comprehensive code integrity and diagnostic checks
---

# Code Integrity Workflow

This workflow ensures the codebase meets the high standards of AtlasTrinity using Ruff, Pyrefly, Oxlint, and Knip.

// turbo-all

1. Run full project diagnostics:
   ```bash
   npm run lint:all
   ```

2. Automatically fix formatting and common lint issues:
   ```bash
   npm run format:write
   ```

3. (Optional) Run Python-only diagnostics:
   ```bash
   npm run lint:py
   ```

4. (Optional) Run TypeScript-only diagnostics:
   ```bash
   npm run lint:ts
   ```

5. (Optional) Check for unused code and dependencies:
   ```bash
   npm run lint:unused
   ```
