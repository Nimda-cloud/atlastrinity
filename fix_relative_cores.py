import os
import re

# Directories to focus on for relative import fixes
CORES = [
    'src/brain/core/orchestration',
    'src/brain/core/server',
    'src/brain/core/services',
    'src/brain/mcp',
    'src/brain/memory',
    'src/brain/monitoring',
    'src/brain/behavior',
    'src/brain/healing',
    'src/brain/navigation',
    'src/brain/infrastructure',
    'src/brain/voice',
    'src/brain/agents',
]

# Map relative base names to their absolute modular counterparts
# This handles "from .X" or "import .X" where X is a moved module
RELATIVE_MAP = {
    'mcp_registry': 'src.brain.mcp.mcp_registry',
    'mcp_manager': 'src.brain.mcp.mcp_manager',
    'mcp_preflight': 'src.brain.mcp.mcp_preflight',
    'mcp_health_dashboard': 'src.brain.mcp.mcp_health_dashboard',
    'map_state': 'src.brain.navigation.map_state',
    'tour_driver': 'src.brain.navigation.tour_driver',
    'tour_manager': 'src.brain.navigation.tour_manager',
    'behavior_engine': 'src.brain.behavior.behavior_engine',
    'adaptive_behavior': 'src.brain.behavior.adaptive_behavior',
    'internal_actions': 'src.brain.behavior.internal_actions',
    'consolidation': 'src.brain.behavior.consolidation',
    'constraint_monitor': 'src.brain.behavior.constraint_monitor',
    'atlas': 'src.brain.agents.atlas',
    'tetyana': 'src.brain.agents.tetyana',
    'grisha': 'src.brain.agents.grisha',
    'base_agent': 'src.brain.agents.base_agent',
    'logger': 'src.brain.monitoring.logger',
    'metrics': 'src.brain.monitoring.metrics',
    'notifications': 'src.brain.monitoring.notifications',
    'watchdog': 'src.brain.monitoring.watchdog',
    'monitoring_config': 'src.brain.monitoring.monitoring_config',
    'monitoring': 'src.brain.monitoring.monitoring',
    'config_loader': 'src.brain.config.config_loader',
    'config_validator': 'src.brain.config.config_validator',
    'config': 'src.brain.config.config',
    'memory': 'src.brain.memory.memory',
    'knowledge_graph': 'src.brain.memory.knowledge_graph',
    'semantic_linker': 'src.brain.memory.semantic_linker',
    'stt': 'src.brain.voice.stt',
    'tts': 'src.brain.voice.tts',
    'orchestration_utils': 'src.brain.voice.orchestration_utils',
    'message_bus': 'src.brain.core.server.message_bus',
    'server': 'src.brain.core.server.server',
    'orchestrator': 'src.brain.core.orchestration.orchestrator',
    'mode_router': 'src.brain.core.orchestration.mode_router',
    'request_segmenter': 'src.brain.core.orchestration.request_segmenter',
    'context': 'src.brain.core.orchestration.context',
    'error_router': 'src.brain.core.orchestration.error_router',
    'tool_dispatcher': 'src.brain.core.orchestration.tool_dispatcher',
    'services_manager': 'src.brain.core.services.services_manager',
    'state_manager': 'src.brain.core.services.state_manager',
    'system_healing': 'src.brain.healing.system_healing',
    'parallel_healing': 'src.brain.healing.parallel_healing',
}

def fix_relative_imports():
    root_dir = '/Users/dev/Documents/GitHub/atlastrinity/'
    updated_count = 0
    
    for core_dir in CORES:
        abs_core = os.path.join(root_dir, core_dir)
        if not os.path.exists(abs_core): continue
        
        for r, d, files in os.walk(abs_core):
            for file in files:
                if file.endswith('.py'):
                    abs_path = os.path.join(r, file)
                    with open(abs_path, encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = content
                    # Target "from .module" and "from ..module"
                    # Pattern matching "from .base" where base is in RELATIVE_MAP
                    for base, abs_target in RELATIVE_MAP.items():
                        # Handle "from .base"
                        new_content = re.sub(rf'from \.{base}\b', f'from {abs_target}', new_content)
                        # Handle "from ..base" (for deeper nesting)
                        new_content = re.sub(rf'from \.\.{base}\b', f'from {abs_target}', new_content)
                        # Handle "from .base.sub"
                        new_content = re.sub(rf'from \.{base}\.', f'from {abs_target}.', new_content)
                        # Handle "from ..base.sub"
                        new_content = re.sub(rf'from \.\.{base}\.', f'from {abs_target}.', new_content)

                    if new_content != content:
                        with open(abs_path, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        updated_count += 1
                        
    print(f"Relative import fix complete. {updated_count} files updated.")

if __name__ == "__main__":
    fix_relative_imports()
