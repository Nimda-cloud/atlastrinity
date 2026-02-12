import os
import re

# Comprehensive mapping from old flat structure to new modular structure
# This includes both the module name and the full path
REPLACEMENTS = {
    # Core Orchestration
    r'src\.brain\.orchestrator': 'src.brain.core.orchestration.orchestrator',
    r'src\.brain\.mode_router': 'src.brain.core.orchestration.mode_router',
    r'src\.brain\.request_segmenter': 'src.brain.core.orchestration.request_segmenter',
    r'src\.brain\.context': 'src.brain.core.orchestration.context',
    r'src\.brain\.error_router': 'src.brain.core.orchestration.error_router',
    r'src\.brain\.tool_dispatcher': 'src.brain.core.orchestration.tool_dispatcher',
    
    # Core Server/Services
    r'src\.brain\.server': 'src.brain.core.server.server',
    r'src\.brain\.message_bus': 'src.brain.core.server.message_bus',
    r'src\.brain\.state_manager': 'src.brain.core.services.state_manager',
    r'src\.brain\.services_manager': 'src.brain.core.services.services_manager',
    
    # Configurations
    r'src\.brain\.config_loader': 'src.brain.config.config_loader',
    r'src\.brain\.config_validator': 'src.brain.config.config_validator',
    r'src\.brain\.config(?!\.[a-z])': 'src.brain.config.config', # Only if it's not already pointing to a submodule
    
    # Monitoring
    r'src\.brain\.logger': 'src.brain.monitoring.logger',
    r'src\.brain\.metrics': 'src.brain.monitoring.metrics',
    r'src\.brain\.monitoring_config': 'src.brain.monitoring.monitoring_config',
    r'src\.brain\.notifications': 'src.brain.monitoring.notifications',
    r'src\.brain\.watchdog': 'src.brain.monitoring.watchdog',
    r'src\.brain\.monitoring(?!\.[a-z])': 'src.brain.monitoring.monitoring',
    
    # MCP
    r'src\.brain\.mcp_manager': 'src.brain.mcp.mcp_manager',
    r'src\.brain\.mcp_registry': 'src.brain.mcp.mcp_registry',
    r'src\.brain\.mcp_preflight': 'src.brain.mcp.mcp_preflight',
    r'src\.brain\.mcp_health_dashboard': 'src.brain.mcp.mcp_health_dashboard',
    
    # Memory
    r'src\.brain\.memory(?!\.[a-z])': 'src.brain.memory.memory',
    r'src\.brain\.knowledge_graph': 'src.brain.memory.knowledge_graph',
    r'src\.brain\.semantic_linker': 'src.brain.memory.semantic_linker',
    r'src\.brain\.db\.manager': 'src.brain.memory.db.manager',
    r'src\.brain\.db\.schema': 'src.brain.memory.db.schema',
    
    # Behavior
    r'src\.brain\.behavior_engine': 'src.brain.behavior.behavior_engine',
    r'src\.brain\.adaptive_behavior': 'src.brain.behavior.adaptive_behavior',
    r'src\.brain\.constraint_monitor': 'src.brain.behavior.constraint_monitor',
    r'src\.brain\.internal_actions': 'src.brain.behavior.internal_actions',
    r'src\.brain\.consolidation': 'src.brain.behavior.consolidation',
    
    # Healing
    r'src\.brain\.system_healing': 'src.brain.healing.system_healing',
    r'src\.brain\.parallel_healing': 'src.brain.healing.parallel_healing',
    
    # Navigation
    r'src\.brain\.map_state': 'src.brain.navigation.map_state',
    r'src\.brain\.tour_driver': 'src.brain.navigation.tour_driver',
    r'src\.brain\.tour_manager': 'src.brain.navigation.tour_manager',
}

# Cleanup potential double/triple nesting introduced by previous runs
CLEANUP = [
    (r'src\.brain\.config\.config\.config', 'src.brain.config.config'),
    (r'src\.brain\.config\.config_loader', 'src.brain.config.config_loader'),
    (r'src\.brain\.monitoring\.monitoring\.monitoring', 'src.brain.monitoring.monitoring'),
    (r'src\.brain\.monitoring\.monitoring', 'src.brain.monitoring.monitoring'),
    (r'src\.brain\.memory\.memory\.memory', 'src.brain.memory.memory'),
    (r'src\.brain\.memory\.memory', 'src.brain.memory.memory'),
    (r'src\.brain\.core\.orchestration\.orchestration', 'src.brain.core.orchestration.orchestrator'),
    (r'src\.brain\.core\.server\.server', 'src.brain.core.server.server'),
    (r'src\.brain\.mcp\.mcp_manager', 'src.brain.mcp.mcp_manager'),
]

def fix_imports(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        
        # 1. Apply primary replacements (longest first)
        for old, new in sorted(REPLACEMENTS.items(), key=lambda x: len(x[0]), reverse=True):
            new_content = re.sub(old, new, new_content)
        
        # 2. Apply cleanup for double nesting
        for old, new in CLEANUP:
            new_content = re.sub(old, new, new_content)
            
        # 3. Final sanity check for double dots or weird patterns
        new_content = new_content.replace('src.brain.config.config_loader', 'src.brain.config.config_loader') # Ensure no extra config.config
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    return False

def main():
    root_dir = '/Users/dev/Documents/GitHub/atlastrinity/'
    updated_count = 0
    
    # Target src and tests
    for target in ['src', 'tests']:
        base_path = os.path.join(root_dir, target)
        if not os.path.exists(base_path):
            continue
            
        for root, _, files in os.walk(base_path):
            for file in files:
                if file.endswith('.py'):
                    if fix_imports(os.path.join(root, file)):
                        updated_count += 1
                        
    print(f"Successfully updated imports in {updated_count} files.")

if __name__ == "__main__":
    main()
