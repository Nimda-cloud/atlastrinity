import os
import re

# Precise mapping for remaining legacy/broken paths
MAPPINGS = {
    'src.brain.request_segmenter': 'src.brain.core.orchestration.request_segmenter',
    'src.brain.knowledge_graph': 'src.brain.memory.knowledge_graph',
    'src.brain.message_bus': 'src.brain.core.server.message_bus',
    'src.brain.context': 'src.brain.core.orchestration.context',
    'src.brain.behavior.agents.atlas': 'src.brain.agents.atlas',
    'src.brain.behavior.db.manager': 'src.brain.memory.db.manager',
    'src.brain.behavior.db.schema': 'src.brain.memory.db.schema',
    'src.brain.core.services_manager': 'src.brain.core.services.services_manager',
    'src.brain.core.orchestration.behavior_engine': 'src.brain.behavior.behavior_engine',
    'src.brain.monitoring.monitoring.metrics': 'src.brain.monitoring.metrics',
    'src.brain.monitoring.monitoring.notifications': 'src.brain.monitoring.notifications',
    'src.brain.monitoring.monitoring.constraint_monitor': 'src.brain.behavior.constraint_monitor',
    'src.brain.core.orchestration.agents.atlas': 'src.brain.agents.atlas',
    'src.brain.core.orchestration.mcp_registry': 'src.brain.mcp.mcp_registry',
    'src.brain.core.orchestration.map_state': 'src.brain.navigation.map_state',
    'src.brain.core.orchestration.navigation.tour_driver': 'src.brain.navigation.tour_driver',
    'src.brain.core.server.db.manager': 'src.brain.memory.db.manager',
    'src.brain.core.server.db.schema': 'src.brain.memory.db.schema',
    'src.brain.core.server.voice.stt': 'src.brain.voice.stt',
    'src.brain.core.server.watchdog': 'src.brain.monitoring.watchdog',
    'src.brain.core.server.services.file_processor': 'src.brain.services.file_processor',
    'src.brain.core.server.map_state': 'src.brain.navigation.map_state',
    'src.brain.infrastructure.db.manager': 'src.brain.memory.db.manager',
    'src.brain.mcp.db.manager': 'src.brain.memory.db.manager',
    'src.brain.mcp.tool_dispatcher': 'src.brain.core.orchestration.tool_dispatcher',
    'src.brain.mcp.behavior_engine': 'src.brain.behavior.behavior_engine',
    'src.brain.monitoring.utils.security': 'src.brain.monitoring.utils.security', # Verify this path?
    'src.brain.map_state': 'src.brain.navigation.map_state',
    'src.brain.behavior.config_loader': 'src.brain.config.config_loader',
    'src.brain.behavior.memory': 'src.brain.memory.memory',
    'src.brain.behavior.logger': 'src.brain.monitoring.logger',
}

# Nesting purge patterns
NESTING_PURGE = [
    (r'memory\.memory\.memory', 'memory'),
    (r'memory\.memory', 'memory'),
    (r'monitoring\.monitoring\.monitoring', 'monitoring'),
    (r'monitoring\.monitoring', 'monitoring'),
    (r'config\.config\.config', 'config'),
    (r'config\.config', 'config'),
    (r'core\.orchestration\.orchestration', 'core.orchestration'),
    (r'core\.server\.server', 'core.server'),
    (r'mcp\.mcp', 'mcp'),
]

def fix_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        
        # 1. Purge nesting first (aggressive)
        for pattern, replacement in NESTING_PURGE:
            new_content = re.sub(pattern, replacement, new_content)
            
        # 2. Apply precise mappings
        for legacy, current in sorted(MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True):
            new_content = new_content.replace(legacy, current)
            
        # 3. Final cleanup of potential artifacts like "...logger" mapping to "logger" and then "monitoring.logger"
        # Ensure src.brain.monitoring.logger doesn't become src.brain.monitoring.monitoring.logger
        new_content = new_content.replace('src.brain.monitoring.monitoring.logger', 'src.brain.monitoring.logger')
        new_content = new_content.replace('src.brain.memory.memory.db.manager', 'src.brain.memory.db.manager')
        new_content = new_content.replace('src.brain.memory.memory.db.schema', 'src.brain.memory.db.schema')

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    except Exception as e:
        print(f"Error fixed in {filepath}: {e}")
    return False

def main():
    root_dir = '/Users/dev/Documents/GitHub/atlastrinity/'
    count = 0
    for target in ['src', 'tests']:
        base = os.path.join(root_dir, target)
        if not os.path.exists(base): continue
        for root, _, files in os.walk(base):
            for file in files:
                if file.endswith('.py'):
                    if fix_file(os.path.join(root, file)):
                        count += 1
    print(f"Definitively fixed {count} files.")

if __name__ == "__main__":
    main()
