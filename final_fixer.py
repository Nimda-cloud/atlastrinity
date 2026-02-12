import os
import re

# Comprehensive modular mapping
replacements = {
    # Core Orchestration
    'src.brain.orchestrator': 'src.brain.core.orchestration.orchestrator',
    'src.brain.mode_router': 'src.brain.core.orchestration.mode_router',
    'src.brain.request_segmenter': 'src.brain.core.orchestration.request_segmenter',
    'src.brain.context': 'src.brain.core.orchestration.context',
    'src.brain.error_router': 'src.brain.core.orchestration.error_router',
    
    # Core Server/Services
    'src.brain.server': 'src.brain.core.server.server',
    'src.brain.message_bus': 'src.brain.core.server.message_bus',
    'src.brain.state_manager': 'src.brain.core.services.state_manager',
    'src.brain.services_manager': 'src.brain.core.services.services_manager',
    
    # Configuration
    'src.brain.config_loader': 'src.brain.config.config_loader',
    'src.brain.config_validator': 'src.brain.config.config_validator',
    
    # Monitoring
    'src.brain.logger': 'src.brain.monitoring.logger',
    'src.brain.monitoring_config': 'src.brain.monitoring.monitoring_config',
    'src.brain.metrics': 'src.brain.monitoring.metrics',
    'src.brain.notifications': 'src.brain.monitoring.notifications',
    'src.brain.watchdog': 'src.brain.monitoring.watchdog',
    
    # Memory
    'src.brain.memory': 'src.brain.memory.memory',
    'src.brain.knowledge_graph': 'src.brain.memory.knowledge_graph',
    'src.brain.semantic_linker': 'src.brain.memory.semantic_linker',
    
    # Behavior
    'src.brain.behavior_engine': 'src.brain.behavior.behavior_engine',
    'src.brain.adaptive_behavior': 'src.brain.behavior.adaptive_behavior',
    'src.brain.constraint_monitor': 'src.brain.behavior.constraint_monitor',
    'src.brain.consolidation': 'src.brain.behavior.consolidation',
    
    # Healing
    'src.brain.parallel_healing': 'src.brain.healing.parallel_healing',
    'src.brain.system_healing': 'src.brain.healing.system_healing',
    
    # Navigation
    'src.brain.map_state': 'src.brain.navigation.map_state',
    'src.brain.tour_driver': 'src.brain.navigation.tour_driver',
    'src.brain.tour_manager': 'src.brain.navigation.tour_manager',
    
    # MCP (ensure sub-module access)
    'src.brain.mcp_manager': 'src.brain.mcp.mcp_manager',
    'src.brain.mcp_registry': 'src.brain.mcp.mcp_registry',
    'src.brain.mcp_preflight': 'src.brain.mcp.mcp_preflight',
}

def process_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        
        # Whole word replacement for src.brain.X
        for old, new in sorted(replacements.items(), key=lambda x: len(x[0]), reverse=True):
            # We want to replace src.brain.X but NOT src.brain.Y.X if Y.X is the new path
            # Regex for exact match but avoiding double replacement
            # Matches src.brain.old if not preceded by the prefix of the new path or something like that
            # Actually, the simplest is to replace only if the string is EXACTLY src.brain.old
            # and not part of a longer src.brain path that is ALREADY new.
            
            pattern = re.escape(old) 
            # If the current file ALREADY has the new path, we might match a substring.
            # Example: src.brain.config.config_loader matches src.brain.config_loader? No, there is a .config. in between.
            # So simple string replace of the most specific (longest) keys first is generally safe.
            
            new_content = new_content.replace(old, new)

        # Cleanup potential double nesting errors from previous attempts
        nesting_fixes = [
            ('monitoring.monitoring', 'monitoring'),
            ('config.config', 'config'),
            ('memory.memory', 'memory'),
            ('core.orchestration.orchestration', 'core.orchestration'),
            ('core.server.server', 'core.server'),
            ('mcp.mcp', 'mcp'),
        ]
        for bad, good in nesting_fixes:
            new_content = new_content.replace(bad, good)
            
        # Fix the "mcp mcp_manager" corruption
        new_content = re.sub(r'from src\.brain\.mcp import mcp_manager', 'from src.brain.mcp.mcp_manager import mcp_manager', new_content)

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    except Exception as e:
        print(f"Error in {filepath}: {e}")
    return False

root = '/Users/dev/Documents/GitHub/atlastrinity/'
count = 0
for r, d, files in os.walk(os.path.join(root, 'src')):
    for f in files:
        if f.endswith('.py') and process_file(os.path.join(r, f)):
            count += 1
for r, d, files in os.walk(os.path.join(root, 'tests')):
    for f in files:
        if f.endswith('.py') and process_file(os.path.join(r, f)):
            count += 1

print(f"Final Fixer updated {count} files.")
