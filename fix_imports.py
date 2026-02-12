import os
import re

replacements = {
    r'src\.brain\.config_loader': 'src.brain.config.config_loader',
    r'src\.brain\.context': 'src.brain.core.orchestration.context',
    r'src\.brain\.logger': 'src.brain.monitoring.logger',
    r'src\.brain\.mcp_manager': 'src.brain.mcp.mcp_manager',
    r'src\.brain\.mode_router': 'src.brain.core.orchestration.mode_router',
    r'src\.brain\.mcp_registry': 'src.brain.mcp.mcp_registry',
    r'src\.brain\.request_segmenter': 'src.brain.core.orchestration.request_segmenter',
    r'src\.brain\.state_manager': 'src.brain.core.services.state_manager',
    r'src\.brain\.knowledge_graph': 'src.brain.memory.knowledge_graph',
    r'src\.brain\.message_bus': 'src.brain.core.server.message_bus',
    r'src\.brain\.server': 'src.brain.core.server.server',
    r'src\.brain\.orchestrator': 'src.brain.core.orchestration.orchestrator',
    r'src\.brain\.db\.schema': 'src.brain.memory.db.schema',
    r'src\.brain\.memory': 'src.brain.memory.memory',
    r'src\.brain\.monitoring': 'src.brain.monitoring.monitoring',
    r'src\.brain\.metrics': 'src.brain.monitoring.metrics',
    r'src\.brain\.notifications': 'src.brain.monitoring.notifications',
    r'src\.brain\.parallel_healing': 'src.brain.healing.parallel_healing',
    r'src\.brain\.tour_driver': 'src.brain.navigation.tour_driver',
    r'src\.brain\.map_state': 'src.brain.navigation.map_state',
    r'src\.brain\.behavior_engine': 'src.brain.behavior.behavior_engine',
    r'src\.brain\.constraint_monitor': 'src.brain.behavior.constraint_monitor',
    # Common relative imports
    r'from \.\.config_loader': 'from src.brain.config.config_loader',
    r'from \.\.logger': 'from src.brain.monitoring.logger',
    r'from \.\.config import': 'from src.brain.config.config import',
    r'from \.\.mcp_manager': 'from src.brain.mcp.mcp_manager',
    r'from \.\.memory': 'from src.brain.memory.memory',
    r'from \.\.mcp_registry': 'from src.brain.mcp.mcp_registry',
    r'from \.\.state_manager': 'from src.brain.core.services.state_manager',
}

def process_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        for pattern, replacement in replacements.items():
            new_content = re.sub(pattern, replacement, new_content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    return False

root_dir = '/Users/dev/Documents/GitHub/atlastrinity/src/brain'
files_updated = 0
for root, dirs, files in os.walk(root_dir):
    for file in files:
        if file.endswith('.py'):
            if process_file(os.path.join(root, file)):
                files_updated += 1

print(f"Updated {files_updated} files.")
