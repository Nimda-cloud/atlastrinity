
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.brain.core.orchestration.error_router import error_router, ErrorCategory
from src.maintenance.system_fixer import SystemFixer

def test_ci_classification():
    print("--- Testing CI Failure Classification ---")
    ci_errors = [
        "Workflow failed: CI Core Pipeline",
        "Action failed: test-python",
        "GitHub Actions failure: exit code 1",
        "Script not found in CI: scripts/ci/check_architecture.py"
    ]
    
    for err in ci_errors:
        category = error_router.classify(err)
        print(f"Error: {err} -> Category: {category.value}")
        assert category == ErrorCategory.CI_FAILURE
    print("✅ Classification passed!")

def test_ci_auto_fix():
    print("\n--- Testing CI Auto-Fix Logic ---")
    fixer = SystemFixer()
    
    # 1. Simulate a broken workflow file
    wf_path = PROJECT_ROOT / ".github/workflows/test_temp.yml"
    wf_path.parent.mkdir(parents=True, exist_ok=True)
    wf_path.write_text("run: python scripts/ci/some_script.py", encoding="utf-8")
    
    print(f"Simulated broken workflow: {wf_path}")
    
    # 2. Run the fixer
    fixer.fix_ci_failures()
    
    # 3. Check if it was fixed
    content = wf_path.read_text(encoding="utf-8")
    if "src/testing/ci/" in content:
        print("✅ Path automatically fixed in workflow!")
    else:
        print("❌ Path WAS NOT fixed in workflow!")
        
    # Cleanup
    wf_path.unlink()

if __name__ == "__main__":
    try:
        test_ci_classification()
        test_ci_auto_fix()
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
