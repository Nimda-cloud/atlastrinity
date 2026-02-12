import os
import re

mappings = {
    'src.brain.config_loader': 'src.brain.config.config_loader',
    'src.brain.knowledge_graph': 'src.brain.memory.knowledge_graph',
    'src.brain.message_bus': 'src.brain.core.server.message_bus',
    'src.brain.context': 'src.brain.core.orchestration.context',
    'src.brain.mode_router': 'src.brain.core.orchestration.mode_router',
    'src.brain.request_segmenter': 'src.brain.core.orchestration.request_segmenter',
    'src.brain.state_manager': 'src.brain.core.services.state_manager',
    'src.brain.services_manager': 'src.brain.core.services.services_manager',
    'src.brain.mcp_manager': 'src.brain.mcp.mcp_manager',
    'src.brain.mcp_registry': 'src.brain.mcp.mcp_registry',
    'src.brain.mcp_preflight': 'src.brain.mcp.mcp_preflight',
    'src.brain.logger': 'src.brain.monitoring.logger',
    'src.brain.monitoring_config': 'src.brain.monitoring.monitoring_config',
    'src.brain.notifications': 'src.brain.monitoring.notifications',
    'src.brain.metrics': 'src.brain.monitoring.metrics',
    'src.brain.parallel_healing': 'src.brain.healing.parallel_healing',
    'src.brain.system_healing': 'src.brain.healing.system_healing',
    'src.brain.map_state': 'src.brain.navigation.map_state',
    'src.brain.tour_driver': 'src.brain.navigation.tour_driver',
    'src.brain.tour_manager': 'src.brain.navigation.tour_manager',
    'src.brain.behavior_engine': 'src.brain.behavior.behavior_engine',
    'src.brain.constraint_monitor': 'src.brain.behavior.constraint_monitor',
    # Cross-package fixes
    'src.brain.behavior.logger': 'src.brain.monitoring.logger',
    'src.brain.config.logger': 'src.brain.monitoring.logger',
    'src.brain.core.orchestration.logger': 'src.brain.monitoring.logger',
    'src.brain.core.server.logger': 'src.brain.monitoring.logger',
    'src.brain.memory.logger': 'src.brain.monitoring.logger',
    'src.brain.mcp.logger': 'src.brain.monitoring.logger',
    'src.brain.behavior.config_loader': 'src.brain.config.config_loader',
    'src.brain.behavior.memory': 'src.brain.memory.memory',
    # Legacy-legacy fixes
    'brain.config_loader': 'src.brain.config.config_loader',
}

def fix_line(line):
    new_line = line
    # Sort keys by length descending to catch longer paths first
    for old, new in sorted(mappings.items(), key=lambda x: len(x[0]), reverse=True):
        if old in new_line:
            # Avoid replacing if it's already the new path
            if new in new_line:
                continue
            new_line = new_line.replace(old, new)
    
    # Cleanup any double nesting introduced during earlier steps
    new_line = new_line.replace('monitoring.monitoring', 'monitoring')
    new_line = new_line.replace('memory.memory', 'memory')
    new_line = new_line.replace('config.config', 'config')
    
    return new_line

def process_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        changed = False
        for line in lines:
            if 'brain' in line:
                fixed = fix_line(line)
                if fixed != line:
                    new_lines.append(fixed)
                    changed = True
                    continue
            new_lines.append(line)
        
        if changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    return False

root_dir = '/Users/dev/Documents/GitHub/atlastrinity/'
files_updated = 0
# Process ALL source files, not just src/brain
for root, dirs, files in os.walk(os.path.join(root_dir, 'src')):
    for file in files:
        if file.endswith('.py'):
            if process_file(os.path.join(root, file)):
                files_updated += 1
# Also check tests
for root, dirs, files in os.walk(os.path.join(root_dir, 'tests')):
    for file in files:
        if file.endswith('.py'):
            if process_file(os.path.join(root, file)):
                files_updated += 1

print(f"Refined surgical fix applied to {files_updated} files.")
