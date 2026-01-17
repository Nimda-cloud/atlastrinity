import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath("src"))

def test_setup():
    print("--- 🔍 Testing Setup Logic ---")
    
    # 1. Test config defaults
    from brain.config_loader import config
    workspace = config.get("system.workspace_path")
    repo_path = config.get("system.repository_path")
    
    print(f"Default Workspace: {workspace}")
    print(f"Default Repo Path: {repo_path}")
    
    if workspace != "~/Developer/Trinity":
        print(f"❌ Error: Unexpected default workspace: {workspace}")
    else:
        print("✅ Default workspace correct.")
        
    # 2. Test directory creation
    from brain.config import ensure_dirs
    # ensure_dirs() is called on import usually, but let's call it again
    ensure_dirs()
    
    ws_path = Path(workspace).expanduser().absolute()
    if ws_path.exists():
        print(f"✅ Directory {ws_path} exists.")
    else:
        print(f"❌ Error: Directory {ws_path} DOES NOT exist.")
        
    # 3. Test vibe_server path resolution
    from mcp_server.vibe_server import PROJECT_ROOT, REPOSITORY_ROOT
    print(f"Vibe PROJECT_ROOT: {PROJECT_ROOT}")
    print(f"Vibe REPOSITORY_ROOT: {REPOSITORY_ROOT}")
    
    if REPOSITORY_ROOT == repo_path or REPOSITORY_ROOT == str(Path(repo_path).expanduser().absolute()):
         print("✅ Vibe REPOSITORY_ROOT matches config.")
    else:
         print(f"⚠️  Vibe REPOSITORY_ROOT ({REPOSITORY_ROOT}) differs from config ({repo_path}) - check symlinks/paths.")

if __name__ == "__main__":
    test_setup()
