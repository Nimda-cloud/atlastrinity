import os
import re

FULL_MAPPING = {
    # Agents
    r'src\.brain\.atlas\b': 'src.brain.agents.atlas',
    r'src\.brain\.tetyana\b': 'src.brain.agents.tetyana',
    r'src\.brain\.grisha\b': 'src.brain.agents.grisha',
    r'src\.brain\.base_agent\b': 'src.brain.agents.base_agent',
    
    # Core Orchestration
    r'src\.brain\.orchestrator\b': 'src.brain.core.orchestration.orchestrator',
    r'src\.brain\.mode_router\b': 'src.brain.core.orchestration.mode_router',
    r'src\.brain\.request_segmenter\b': 'src.brain.core.orchestration.request_segmenter',
    r'src\.brain\.context\b': 'src.brain.core.orchestration.context',
    r'src\.brain\.error_router\b': 'src.brain.core.orchestration.error_router',
    r'src\.brain\.tool_dispatcher\b': 'src.brain.core.orchestration.tool_dispatcher',
    
    # Core Server/Services
    r'src\.brain\.server\b': 'src.brain.core.server.server',
    r'src\.brain\.message_bus\b': 'src.brain.core.server.message_bus',
    r'src\.brain\.state_manager\b': 'src.brain.core.services.state_manager',
    r'src\.brain\.services_manager\b': 'src.brain.core.services.services_manager',
    r'src\.brain\.file_processor\b': 'src.brain.services.file_processor',
    
    # Config
    r'src\.brain\.config_loader\b': 'src.brain.config.config_loader',
    r'src\.brain\.config_validator\b': 'src.brain.config.config_validator',
    r'src\.brain\.config\b': 'src.brain.config.config',
    
    # MCP
    r'src\.brain\.mcp_manager\b': 'src.brain.mcp.mcp_manager',
    r'src\.brain\.mcp_registry\b': 'src.brain.mcp.mcp_registry',
    r'src\.brain\.mcp_preflight\b': 'src.brain.mcp.mcp_preflight',
    
    # Monitoring
    r'src\.brain\.logger\b': 'src.brain.monitoring.logger',
    r'src\.brain\.metrics\b': 'src.brain.monitoring.metrics',
    r'src\.brain\.monitoring_config\b': 'src.brain.monitoring.monitoring_config',
    r'src\.brain\.notifications\b': 'src.brain.monitoring.notifications',
    r'src\.brain\.monitoring\b': 'src.brain.monitoring.monitoring',
    
    # Memory & DB
    r'src\.brain\.memory\b': 'src.brain.memory.memory',
    r'src\.brain\.knowledge_graph\b': 'src.brain.memory.knowledge_graph',
    r'src\.brain\.db\.manager\b': 'src.brain.memory.db.manager',
    r'src\.brain\.db\.schema\b': 'src.brain.memory.db.schema',
    
    # Behavior
    r'src\.brain\.behavior_engine\b': 'src.brain.behavior.behavior_engine',
    r'src\.brain\.adaptive_behavior\b': 'src.brain.behavior.adaptive_behavior',
    r'src\.brain\.constraint_monitor\b': 'src.brain.behavior.constraint_monitor',
    r'src\.brain\.internal_actions\b': 'src.brain.behavior.internal_actions',
    
    # Healing
    r'src\.brain\.parallel_healing\b': 'src.brain.healing.parallel_healing',
    r'src\.brain\.system_healing\b': 'src.brain.healing.system_healing',
    
    # Navigation
    r'src\.brain\.map_state\b': 'src.brain.navigation.map_state',
    r'src\.brain\.tour_driver\b': 'src.brain.navigation.tour_driver',
    r'src\.brain\.tour_manager\b': 'src.brain.navigation.tour_manager',
    
    # Voice
    r'src\.brain\.stt\b': 'src.brain.voice.stt',
    r'src\.brain\.tts\b': 'src.brain.voice.tts',
    r'src\.brain\.orchestration_utils\b': 'src.brain.voice.orchestration_utils',
}

def fix_imports_total(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        
        # Apply all absolute mappings strictly
        for old_regex, new_path in sorted(FULL_MAPPING.items(), key=lambda x: len(x[0]), reverse=True):
            # We use \b in regex to ensure exact module names
            # But wait, python's re.sub is good here.
            # However, if we already have the new path, we don't want to replace part of it.
            # Example: src.brain.agents.atlas already has "src.brain.atlas" as a substring? No, "atlas" is preceded by "agents.".
            # So a simple re.sub with word boundaries is safe.
            new_content = re.sub(old_regex, new_path, new_content)

        # Catch specific common missed patterns from pyrefly
        # Like from .behavior.agents.atlas
        new_content = new_content.replace('from .behavior.agents.atlas', 'from src.brain.agents.atlas')
        new_content = new_content.replace('from .behavior.memory', 'from src.brain.memory.memory')
        new_content = new_content.replace('from .behavior.db.manager', 'from src.brain.memory.db.manager')
        new_content = new_content.replace('from .behavior.db.schema', 'from src.brain.memory.db.schema')
        new_content = new_content.replace('from .core.services_manager', 'from src.brain.core.services.services_manager')
        new_content = new_content.replace('from .core.orchestration.behavior_engine', 'from src.brain.behavior.behavior_engine')
        new_content = new_content.replace('from .monitoring.constraint_monitor', 'from src.brain.behavior.constraint_monitor')
        new_content = new_content.replace('from .core.orchestration.agents.atlas', 'from src.brain.agents.atlas')
        new_content = new_content.replace('from .core.orchestration.mcp_registry', 'from src.brain.mcp.mcp_registry')
        new_content = new_content.replace('from .core.orchestration.map_state', 'from src.brain.navigation.map_state')
        new_content = new_content.replace('from .core.orchestration.navigation.tour_driver', 'from src.brain.navigation.tour_driver')
        new_content = new_content.replace('from .core.server.db.manager', 'from src.brain.memory.db.manager')
        new_content = new_content.replace('from .core.server.db.schema', 'from src.brain.memory.db.schema')
        new_content = new_content.replace('from .core.server.voice.stt', 'from src.brain.voice.stt')
        new_content = new_content.replace('from .core.server.watchdog', 'from src.brain.monitoring.watchdog')
        new_content = new_content.replace('from .core.server.services.file_processor', 'from src.brain.services.file_processor')
        new_content = new_content.replace('from .core.server.map_state', 'from src.brain.navigation.map_state')
        
        # Double nesting cleanup
        new_content = new_content.replace('src.brain.memory.memory.memory', 'src.brain.memory.memory')
        new_content = new_content.replace('src.brain.config.config.config', 'src.brain.config.config')
        new_content = new_content.replace('src.brain.monitoring.monitoring.monitoring', 'src.brain.monitoring.monitoring')
        new_content = new_content.replace('src.brain.monitoring.monitoring.logger', 'src.brain.monitoring.logger')

        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
    except Exception as e:
        print(f"Error in {filepath}: {e}")
    return False

def main():
    root_dir = '/Users/dev/Documents/GitHub/atlastrinity/'
    count = 0
    for target in ['src', 'tests']:
        for root, _, files in os.walk(os.path.join(root_dir, target)):
            for file in files:
                if file.endswith('.py'):
                    if fix_imports_total(os.path.join(root, file)):
                        count += 1
    print(f"Totally realigned {count} files.")

if __name__ == "__main__":
    main()
