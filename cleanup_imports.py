import os
import re

# Precise replacement rules
absolute_mappings = {
    'src.brain.orchestrator': 'src.brain.core.orchestration.orchestrator',
    'src.brain.mode_router': 'src.brain.core.orchestration.mode_router',
    'src.brain.request_segmenter': 'src.brain.core.orchestration.request_segmenter',
    'src.brain.context': 'src.brain.core.orchestration.context',
    'src.brain.server': 'src.brain.core.server.server',
    'src.brain.message_bus': 'src.brain.core.server.message_bus',
    'src.brain.state_manager': 'src.brain.core.services.state_manager',
    'src.brain.services_manager': 'src.brain.core.services.services_manager',
    'src.brain.mcp_manager': 'src.brain.mcp.mcp_manager',
    'src.brain.mcp_registry': 'src.brain.mcp.mcp_registry',
    'src.brain.mcp_preflight': 'src.brain.mcp.mcp_preflight',
    'src.brain.config_loader': 'src.brain.config.config_loader',
    'src.brain.config': 'src.brain.config.config',
    'src.brain.logger': 'src.brain.monitoring.logger',
    'src.brain.monitoring': 'src.brain.monitoring.monitoring',
    'src.brain.metrics': 'src.brain.monitoring.metrics',
    'src.brain.notifications': 'src.brain.monitoring.notifications',
    'src.brain.monitoring_config': 'src.brain.monitoring.monitoring_config',
    'src.brain.memory': 'src.brain.memory.memory',
    'src.brain.knowledge_graph': 'src.brain.memory.knowledge_graph',
    'src.brain.db.manager': 'src.brain.memory.db.manager',
    'src.brain.db.schema': 'src.brain.memory.db.schema',
    'src.brain.behavior_engine': 'src.brain.behavior.behavior_engine',
    'src.brain.constraint_monitor': 'src.brain.behavior.constraint_monitor',
    'src.brain.adaptive_behavior': 'src.brain.behavior.adaptive_behavior',
    'src.brain.parallel_healing': 'src.brain.healing.parallel_healing',
    'src.brain.system_healing': 'src.brain.healing.system_healing',
    'src.brain.map_state': 'src.brain.navigation.map_state',
    'src.brain.tour_driver': 'src.brain.navigation.tour_driver',
    'src.brain.tour_manager': 'src.brain.navigation.tour_manager',
}

def clean_and_fix(content):
    # 1. First, fix the double/triple nesting issues from previous failed attempts
    # Replace any src.brain.X.X.X with src.brain.X
    for key, val in absolute_mappings.items():
        # Example: src.brain.monitoring.monitoring.monitoring.logger -> src.brain.monitoring.logger
        # We look for the final component
        new_suffix = val.replace('src.brain.', '')
        # Pattern to match repeated versions of the new path
        # If val is src.brain.monitoring.logger, we might find src.brain.monitoring.monitoring.logger
        # We want to replace it with src.brain.monitoring.logger
        
        # Simpler: just replace any "monitoring.monitoring" with "monitoring" etc.
        parts = new_suffix.split('.')
        for part in parts:
            pattern = re.escape(part) + r'\.' + re.escape(part)
            content = re.sub(pattern, part, content)
            
    # 2. Apply absolute mappings strictly (matching whole words for the full string)
    # We use a trick: search for 'src.brain.[something]' and if that something matches a key, replace it.
    def replace_func(match):
        full_path = match.group(0)
        # Check if the full path matches any of our known targets
        for key in sorted(absolute_mappings.keys(), key=len, reverse=True):
            if full_path.startswith(key):
                # We found a match. Replace the legacy part with the new part.
                # Avoid double nested replacement by checking if it's already fixed
                if absolute_mappings[key] in full_path:
                     return full_path
                return full_path.replace(key, absolute_mappings[key])
        return full_path

    # This regex matches src.brain followed by letters, numbers, dots, underscores
    content = re.sub(r'src\.brain\.[a-zA-Z0-9_\.]+', replace_func, content)
    
    # 3. Final cleanup of potential double-dots or errors
    content = content.replace('src.brain.config.config.config', 'src.brain.config.config')
    content = content.replace('src.brain.monitoring.monitoring.monitoring', 'src.brain.monitoring.monitoring')
    content = content.replace('src.brain.memory.memory.memory', 'src.brain.memory.memory')

    return content

def process_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        
        new_content = clean_and_fix(content)
        
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

print(f"Cleaned up and fixed {files_updated} files.")
