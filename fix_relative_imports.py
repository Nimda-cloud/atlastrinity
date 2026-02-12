import os
import re

# Precise mapping for any import that was previously local to src/brain
# We target 'from .module' where module is one of the following:
LOCAL_MODULES_TO_ABS = {
    'logger': 'src.brain.monitoring.logger',
    'config': 'src.brain.config.config',
    'config_loader': 'src.brain.config.config_loader',
    'mcp_manager': 'src.brain.mcp.mcp_manager',
    'state_manager': 'src.brain.core.services.state_manager',
    'services_manager': 'src.brain.core.services.services_manager',
    'message_bus': 'src.brain.core.server.message_bus',
    'context': 'src.brain.core.orchestration.context',
    'mode_router': 'src.brain.core.orchestration.mode_router',
    'request_segmenter': 'src.brain.core.orchestration.request_segmenter',
    'orchestrator': 'src.brain.core.orchestration.orchestrator',
    'memory': 'src.brain.memory.memory',
    'knowledge_graph': 'src.brain.memory.knowledge_graph',
    'monitoring': 'src.brain.monitoring.monitoring',
    'metrics': 'src.brain.monitoring.metrics',
}

def fix_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        changed = False
        for line in lines:
            # Check for "from .module import"
            match = re.match(r'^(\s*)from \.([a-zA-Z0-9_]+) import', line)
            if match:
                prefix = match.group(1)
                module = match.group(2)
                if module in LOCAL_MODULES_TO_ABS:
                    new_line = line.replace(f'.{module}', LOCAL_MODULES_TO_ABS[module])
                    new_lines.append(new_line)
                    changed = True
                    continue
            
            # Also handle absolute imports that might have been partially fixed or double-nested
            fixed_line = line
            # Specific recurring bad patterns from pyrefly
            bad_fixes = [
                ('src.brain.monitoring.monitoring.logger', 'src.brain.monitoring.logger'),
                ('src.brain.config.config.config_loader', 'src.brain.config.config_loader'),
                ('src.brain.memory.memory.memory', 'src.brain.memory.memory'),
                ('src.brain.core.orchestration.logger', 'src.brain.monitoring.logger'),
                ('src.brain.core.server.logger', 'src.brain.monitoring.logger'),
                ('src.brain.behavior.logger', 'src.brain.monitoring.logger'),
                ('src.brain.mcp.logger', 'src.brain.monitoring.logger'),
                ('src.brain.config.logger', 'src.brain.monitoring.logger'),
                ('src.brain.memory.logger', 'src.brain.monitoring.logger'),
                ('src.brain.core.services.logger', 'src.brain.monitoring.logger'),
                ('src.brain.infrastructure.logger', 'src.brain.monitoring.logger'),
            ]
            for bad, good in bad_fixes:
                if bad in fixed_line:
                    fixed_line = fixed_line.replace(bad, good)
            
            if fixed_line != line:
                new_lines.append(fixed_line)
                changed = True
                continue
                
            new_lines.append(line)
            
        if changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            return True
    except Exception as e:
        print(f"Error in {filepath}: {e}")
    return False

def main():
    root_dir = '/Users/dev/Documents/GitHub/atlastrinity/src/brain'
    count = 0
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                if fix_file(os.path.join(root, file)):
                    count += 1
    print(f"Fixed relative/corrupted imports in {count} files.")

if __name__ == "__main__":
    main()
