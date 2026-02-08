import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

class SandboxRunner:
    """
    Executes code in a temporary sandbox environment to verify fixes
    without risking the main codebase stability.
    """

    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root).resolve()
        self.sandbox_dir = Path(tempfile.gettempdir()) / "atlastrinity_sandbox"
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)

    def prepare_sandbox(self, target_file: str, reproduction_script: str) -> str:
        """
        Copies the target file and reproduction script to the sandbox.
        Returns the path to the sandboxed target file.
        """
        # Create a unique isolation request ID
        import uuid

        run_id = str(uuid.uuid4())[:8]
        run_dir = self.sandbox_dir / run_id
        run_dir.mkdir(exist_ok=True)

        target_path = Path(target_file).resolve()
        script_path = Path(reproduction_script).resolve()

        if not target_path.exists():
            raise FileNotFoundError(f"Target file not found: {target_file}")
        if not script_path.exists():
            raise FileNotFoundError(f"Reproduction script not found: {reproduction_script}")

        # preserve directory structure relative to workspace root (simplified)
        # For now, we just copy flat for simplicity, or we can try to replicate imports if needed.
        # A robust sandbox needs PYTHONPATH setup.

        # Strategy:
        # Instead of moving files to a truly isolated folder which breaks imports,
        # we create a 'shadow' temp file in the SAME directory if possible, OR
        # better: we run the reproduction script in a subprocess with the MODIFIED content
        # written to a temporary file, and we tell python to use that.
        #
        # BUT the requirement is "Verify fix without breaking main repo".
        # So we should modify a COPY of the file.

        # Best approach for python imports:
        # 1. Copy the entire necessary module tree? (Too slow)
        # 2. Use `unittest.mock` to patch the module in memory? (Complex for external scripts)
        # 3. Rename the original file -> .bak, write new content, run test, revert? (Risky if crash)
        # 4. Write new content to `file_fixed.py`, and have verification script import THAT.

        # Let's go with Option 4 strategy but simplified:
        # The 'sandbox' here implies logic verification.
        # We will assume the reproduction script is smart enough or we wrap the execution.

        # For this implementation, we will simulate a sandbox by:
        # 1. Reading the content of target_file.
        # 2. Applying the proposed fix (in memory/temp file).
        # 3. But wait, this tool is called AFTER the fix is planned.
        # Actually in the workflow, we copy `target_file` to `target_file.sandbox.py`,
        # apply fix there, and run `verification_script` pointing to `target_file.sandbox.py`.

        sandboxed_target = run_dir / target_path.name
        shutil.copy2(target_path, sandboxed_target)

        sandboxed_script = run_dir / script_path.name
        shutil.copy2(script_path, sandboxed_script)

        return str(run_dir)

    def run_verification(self, run_dir: str, script_name: str) -> tuple[bool, str, str]:
        """
        Runs the verification script within the sandbox directory.
        """
        r_dir = Path(run_dir)
        script_path = r_dir / script_name

        # We must confirm the script exists
        if not script_path.exists():
            return False, "", f"Script {script_name} missing in sandbox {run_dir}"

        # We need to set PYTHONPATH so it can import the project modules if needed
        # We might need to include the workspace root in PYTHONPATH
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{self.workspace_root}:{env.get('PYTHONPATH', '')}"

        try:
            # Run with timeout
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self.workspace_root),  # CWD is root so imports work
                env=env,
                capture_output=True,
                text=True,
                timeout=30,  # 30s timeout for tests
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            return False, "", "Verification Sandbox Timeout (30s)"
        except Exception as e:
            return False, "", str(e)

# Singleton for easy import
sandbox_runner = SandboxRunner(os.getcwd())
