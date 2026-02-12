import os

# Files identified by grep as having legacy imports
TARGET_FILES = [
    'src/brain/memory/db/manager.py',
    'src/brain/config/config.py',
    'src/brain/agents/base_agent.py',
    'src/brain/agents/grisha.py',
    'src/brain/agents/atlas.py',
    'src/brain/agents/tetyana.py',
    'src/brain/mcp/mcp_manager.py',
    'src/brain/voice/tts.py',
    'src/brain/voice/stt.py',
    'src/brain/monitoring/monitoring_config.py',
    'src/brain/infrastructure/first_run_installer.py',
    'src/mcp_server/whisper_server.py',
    'src/mcp_server/redis_server.py',
    'tests/macos_tools/test_global_env.py',
    'tests/test_whisper_mps.py',
]

REPLACEMENTS = {
    'from src.brain.config_loader import': 'from src.brain.config.config_loader import',
    'import src.brain.config_loader': 'import src.brain.config.config_loader',
    'from src.brain.mcp_manager import': 'from src.brain.mcp.mcp_manager import',
    'from src.brain.mcp_registry import': 'from src.brain.mcp.mcp_registry import',
    'from src.brain.request_segmenter import': 'from src.brain.core.orchestration.request_segmenter import',
    'from src.brain.context import': 'from src.brain.core.orchestration.context import',
    'from src.brain.message_bus import': 'from src.brain.core.server.message_bus import',
    'from src.brain.knowledge_graph import': 'from src.brain.memory.knowledge_graph import',
}

def fix_imports_surgically():
    root_dir = '/Users/dev/Documents/GitHub/atlastrinity/'
    updated_count = 0
    for rel_path in TARGET_FILES:
        abs_path = os.path.join(root_dir, rel_path)
        if not os.path.exists(abs_path):
            print(f"Skipping {rel_path}: Not found")
            continue
            
        with open(abs_path, encoding='utf-8') as f:
            content = f.read()
            
        new_content = content
        for old, new in REPLACEMENTS.items():
            new_content = new_content.replace(old, new)
            
        if new_content != content:
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {rel_path}")
            updated_count += 1
        else:
            print(f"No changes needed for {rel_path}")
            
    print(f"Surgical fix complete. {updated_count} files updated.")

if __name__ == "__main__":
    fix_imports_surgically()
