import os
import re

# Precise mapping using word boundaries to avoid double nesting
replacements = {
    # Core orchestration
    r'\bsrc\.brain\.orchestrator\b': 'src.brain.core.orchestration.orchestrator',
    r'\bsrc\.brain\.mode_router\b': 'src.brain.core.orchestration.mode_router',
    r'\bsrc\.brain\.request_segmenter\b': 'src.brain.core.orchestration.request_segmenter',
    r'\bsrc\.brain\.context\b': 'src.brain.core.orchestration.context',
    
    # Core server/services
    r'\bsrc\.brain\.server\b': 'src.brain.core.server.server',
    r'\bsrc\.brain\.message_bus\b': 'src.brain.core.server.message_bus',
    r'\bsrc\.brain\.state_manager\b': 'src.brain.core.services.state_manager',
    r'\bsrc\.brain\.services_manager\b': 'src.brain.core.services.services_manager',
    
    # MCP
    r'\bsrc\.brain\.mcp_manager\b': 'src.brain.mcp.mcp_manager',
    r'\bsrc\.brain\.mcp_registry\b': 'src.brain.mcp.mcp_registry',
    r'\bsrc\.brain\.mcp_preflight\b': 'src.brain.mcp.mcp_preflight',
    
    # Config
    r'\bsrc\.brain\.config_loader\b': 'src.brain.config.config_loader',
    r'\bsrc\.brain\.config\b': 'src.brain.config.config',
    
    # Monitoring
    r'\bsrc\.brain\.logger\b': 'src.brain.monitoring.logger',
    r'\bsrc\.brain\.monitoring\b': 'src.brain.monitoring.monitoring',
    r'\bsrc\.brain\.metrics\b': 'src.brain.monitoring.metrics',
    r'\bsrc\.brain\.notifications\b': 'src.brain.monitoring.notifications',
    r'\bsrc\.brain\.monitoring_config\b': 'src.brain.monitoring.monitoring_config',
    
    # Memory
    r'\bsrc\.brain\.memory\b': 'src.brain.memory.memory',
    r'\bsrc\.brain\.knowledge_graph\b': 'src.brain.memory.knowledge_graph',
    r'\bsrc\.brain\.db\.manager\b': 'src.brain.memory.db.manager',
    r'\bsrc\.brain\.db\.schema\b': 'src.brain.memory.db.schema',
    
    # Behavior
    r'\bsrc\.brain\.behavior_engine\b': 'src.brain.behavior.behavior_engine',
    r'\bsrc\.brain\.constraint_monitor\b': 'src.brain.behavior.constraint_monitor',
    r'\bsrc\.brain\.adaptive_behavior\b': 'src.brain.behavior.adaptive_behavior',
    
    # Healing
    r'\bsrc\.brain\.parallel_healing\b': 'src.brain.healing.parallel_healing',
    r'\bsrc\.brain\.system_healing\b': 'src.brain.healing.system_healing',
    
    # Navigation
    r'\bsrc\.brain\.map_state\b': 'src.brain.navigation.map_state',
    r'\bsrc\.brain\.tour_driver\b': 'src.brain.navigation.tour_driver',
    r'\bsrc\.brain\.tour_manager\b': 'src.brain.navigation.tour_manager',

    # Specific Fixes for double nesting introduced by previous script
    r'src\.brain\.monitoring\.monitoring\.logger': 'src.brain.monitoring.logger',
    r'src\.brain\.config\.config_loader': 'src.brain.config.config_loader',
    r'src\.brain\.memory\.memory\.db\.manager': 'src.brain.memory.db.manager',
}

# Fix relative imports that were broken by moving files
# This is tricky because ".." depends on the file's NEW depth.
# It's safer to convert them to absolute imports.

def process_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        
        # 1. First, convert known problematic relative imports to absolute
        rel_to_abs = {
            r'from \.\.config_loader': 'from src.brain.config.config_loader',
            r'from \.\.logger': 'from src.brain.monitoring.logger',
            r'from \.\.config import': 'from src.brain.config.config import',
            r'from \.\.mcp_manager': 'from src.brain.mcp.mcp_manager',
            r'from \.\.memory': 'from src.brain.memory.memory',
            r'from \.\.mcp_registry': 'from src.brain.mcp.mcp_registry',
            r'from \.\.state_manager': 'from src.brain.core.services.state_manager',
            r'from \.\.behavior_engine': 'from src.brain.behavior.behavior_engine',
            r'from \.\.db\.schema': 'from src.brain.memory.db.schema',
            r'from \.\.db\.manager': 'from src.brain.memory.db.manager',
        }
        
        for pattern, replacement in rel_to_abs.items():
            new_content = re.sub(pattern, replacement, new_content)

        # 2. Then apply absolute path transformations
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
