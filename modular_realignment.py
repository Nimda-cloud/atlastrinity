import os

# Files to scan (the whole project)
ROOT_DIR = '/Users/dev/Documents/GitHub/atlastrinity/'

# Definitive modular mapping to correct misplaced "deep" modular paths
MODULAR_REALIGNMENT = {
    'src.brain.core.orchestration.mcp_registry': 'src.brain.mcp.mcp_registry',
    'src.brain.core.orchestration.mcp_manager': 'src.brain.mcp.mcp_manager',
    'src.brain.core.orchestration.mcp_preflight': 'src.brain.mcp.mcp_preflight',
    'src.brain.core.orchestration.map_state': 'src.brain.navigation.map_state',
    'src.brain.core.orchestration.navigation.tour_driver': 'src.brain.navigation.tour_driver',
    'src.brain.core.orchestration.behavior_engine': 'src.brain.behavior.behavior_engine',
    'src.brain.core.orchestration.adaptive_behavior': 'src.brain.behavior.adaptive_behavior',
    'src.brain.core.orchestration.constraint_monitor': 'src.brain.behavior.constraint_monitor',
    'src.brain.core.orchestration.agents.atlas': 'src.brain.agents.atlas',
    'src.brain.core.orchestration.agents.tetyana': 'src.brain.agents.tetyana',
    'src.brain.core.orchestration.agents.grisha': 'src.brain.agents.grisha',
    
    'src.brain.core.server.voice.stt': 'src.brain.voice.stt',
    'src.brain.core.server.voice.tts': 'src.brain.voice.tts',
    'src.brain.core.server.watchdog': 'src.brain.monitoring.watchdog',
    'src.brain.core.server.metrics': 'src.brain.monitoring.metrics',
    'src.brain.core.server.notifications': 'src.brain.monitoring.notifications',
    'src.brain.core.server.db.manager': 'src.brain.memory.db.manager',
    'src.brain.core.server.db.schema': 'src.brain.memory.db.schema',
    'src.brain.core.server.map_state': 'src.brain.navigation.map_state',
    'src.brain.core.server.services.file_processor': 'src.brain.services.file_processor',
    
    'src.brain.mcp.behavior_engine': 'src.brain.behavior.behavior_engine',
    'src.brain.mcp.tool_dispatcher': 'src.brain.core.orchestration.tool_dispatcher',
    
    'src.brain.behavior.agents.atlas': 'src.brain.agents.atlas',
    'src.brain.behavior.db.manager': 'src.brain.memory.db.manager',
    'src.brain.behavior.db.schema': 'src.brain.memory.db.schema',
}

def realign_modular_imports():
    updated_count = 0
    for target in ['src', 'tests']:
        base = os.path.join(ROOT_DIR, target)
        if not os.path.exists(base): continue
        for r, d, files in os.walk(base):
            for file in files:
                if file.endswith('.py'):
                    abs_path = os.path.join(r, file)
                    with open(abs_path, encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    for old, new in sorted(MODULAR_REALIGNMENT.items(), key=lambda x: len(x[0]), reverse=True):
                        new_content = new_content.replace(old, new)
                    
                    if new_content != content:
                        with open(abs_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        updated_count += 1
                        
    print(f"Modular realignment complete. {updated_count} files updated.")

if __name__ == "__main__":
    realign_modular_imports()
