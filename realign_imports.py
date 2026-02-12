import os
import re

# Comprehensive mapping for all backend relocations
MAPPINGS = {
    # Configuration
    'src.brain.config_loader': 'src.brain.config.config_loader',
    'src.brain.config_validator': 'src.brain.config.config_validator',
    'src.brain.config': 'src.brain.config.config',
    
    # MCP
    'src.brain.mcp_manager': 'src.brain.mcp.mcp_manager',
    'src.brain.mcp_registry': 'src.brain.mcp.mcp_registry',
    'src.brain.mcp_preflight': 'src.brain.mcp.mcp_preflight',
    'src.brain.mcp_health_dashboard': 'src.brain.mcp.mcp_health_dashboard',
    
    # Monitoring
    'src.brain.logger': 'src.brain.monitoring.logger',
    'src.brain.metrics': 'src.brain.monitoring.metrics',
    'src.brain.notifications': 'src.brain.monitoring.notifications',
    'src.brain.monitoring_config': 'src.brain.monitoring.monitoring_config',
    'src.brain.watchdog': 'src.brain.monitoring.watchdog',
    'src.brain.monitoring': 'src.brain.monitoring.monitoring',
    
    # Memory
    'src.brain.knowledge_graph': 'src.brain.memory.knowledge_graph',
    'src.brain.semantic_linker': 'src.brain.memory.semantic_linker',
    'src.brain.memory': 'src.brain.memory.memory',
    'src.brain.db.manager': 'src.brain.memory.db.manager',
    'src.brain.db.schema': 'src.brain.memory.db.schema',
    
    # Core Orchestration
    'src.brain.orchestrator': 'src.brain.core.orchestration.orchestrator',
    'src.brain.mode_router': 'src.brain.core.orchestration.mode_router',
    'src.brain.request_segmenter': 'src.brain.core.orchestration.request_segmenter',
    'src.brain.context': 'src.brain.core.orchestration.context',
    'src.brain.error_router': 'src.brain.core.orchestration.error_router',
    'src.brain.tool_dispatcher': 'src.brain.core.orchestration.tool_dispatcher',
    
    # Core Server/Services
    'src.brain.server': 'src.brain.core.server.server',
    'src.brain.message_bus': 'src.brain.core.server.message_bus',
    'src.brain.services_manager': 'src.brain.core.services.services_manager',
    'src.brain.state_manager': 'src.brain.core.services.state_manager',
    
    # Behavior
    'src.brain.behavior_engine': 'src.brain.behavior.behavior_engine',
    r'src\.brain\.adaptive_behavior': 'src.brain.behavior.adaptive_behavior',
    'src.brain.constraint_monitor': 'src.brain.behavior.constraint_monitor',
    'src.brain.internal_actions': 'src.brain.behavior.internal_actions',
    'src.brain.consolidation': 'src.brain.behavior.consolidation',
    
    # Healing
    'src.brain.system_healing': 'src.brain.healing.system_healing',
    'src.brain.parallel_healing': 'src.brain.healing.parallel_healing',
    
    # Navigation
    'src.brain.map_state': 'src.brain.navigation.map_state',
    'src.brain.tour_driver': 'src.brain.navigation.tour_driver',
    'src.brain.tour_manager': 'src.brain.navigation.tour_manager',
    
    # Voice
    'src.brain.stt': 'src.brain.voice.stt',
    'src.brain.tts': 'src.brain.voice.tts',
    'src.brain.orchestration_utils': 'src.brain.voice.orchestration_utils',
    
    # Agents
    'src.brain.atlas': 'src.brain.agents.atlas',
    'src.brain.tetyana': 'src.brain.agents.tetyana',
    'src.brain.grisha': 'src.brain.agents.grisha',
    'src.brain.base_agent': 'src.brain.agents.base_agent',
}

# Cleanup patterns for double/triple nesting introduced previously
CLEANUP = [
    (r'monitoring\.monitoring\.monitoring', 'monitoring'),
    (r'monitoring\.monitoring', 'monitoring'),
    (r'memory\.memory\.memory', 'memory'),
    (r'memory\.memory', 'memory'),
    (r'config\.config\.config', 'config'),
    (r'config\.config', 'config'),
    (r'core\.orchestration\.orchestration', 'core.orchestration'),
    (r'mcp\.mcp', 'mcp'),
]

def fix_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        
        # 1. Apply primary mappings (longest first to avoid partial matches)
        # We use strict matching for these absolute paths
        for legacy, current in sorted(MAPPINGS.items(), key=lambda x: len(x[0]), reverse=True):
            # Check for matches that aren't already fixed
            # Regex to match src.brain.X but NOT if it's already part of the new path if the new path contains it
            # Simple approach: replace legacy and THEN cleanup double nesting
            new_content = new_content.replace(legacy, current)
            
        # 2. Cleanup double nesting
        for pattern, replacement in CLEANUP:
            new_content = re.sub(pattern, replacement, new_content)
            
        # 3. Specific fix for relative imports in brain modules
        # Replace "from .module" with absolute if it's one of the legacy modules
        # This is trickier as it depends on where the file is. 
        # But we can target common broken ones like ".logger", ".config_loader"
        relative_fixes = {
            r'from \.logger': 'from src.brain.monitoring.logger',
            r'from \.config_loader': 'from src.brain.config.config_loader',
            r'from \.config': 'from src.brain.config.config',
            r'from \.mcp_manager': 'from src.brain.mcp.mcp_manager',
            r'from \.memory': 'from src.brain.memory.memory',
            r'from \.db\.manager': 'from src.brain.memory.db.manager',
            r'from \.db\.schema': 'from src.brain.memory.db.schema',
        }
        for rel, abs_path in relative_fixes.items():
            new_content = re.sub(rel, abs_path, new_content)

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    except Exception as e:
        print(f"Error fixed in {filepath}: {e}")
    return False

def main():
    root = '/Users/dev/Documents/GitHub/atlastrinity/'
    count = 0
    for target in ['src', 'tests']:
        base = os.path.join(root, target)
        if not os.path.exists(base): continue
        for r, d, files in os.walk(base):
            for file in files:
                if file.endswith('.py'):
                    if fix_file(os.path.join(r, file)):
                        count += 1
    print(f"Succesfully realigned imports in {count} files.")

if __name__ == "__main__":
    main()
