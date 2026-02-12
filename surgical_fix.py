import os
import re


def fix_corrupted_line(line):
    # 1. Fix the double/triple nesting for all packages
    # Patterns like monitoring.monitoring.monitoring -> monitoring
    # but we need to stay within src.brain
    
    # Let's target specific known bad nested patterns
    bad_patterns = [
        ('monitoring.monitoring.monitoring', 'monitoring'),
        ('monitoring.monitoring', 'monitoring'),
        ('memory.memory.memory', 'memory'),
        ('memory.memory', 'memory'),
        ('config.config.config', 'config'),
        ('config.config', 'config'),
        ('core.orchestration.orchestration', 'core.orchestration'),
        ('core.server.server.server', 'core.server'),
        ('core.server.server', 'core.server'),
    ]
    
    new_line = line
    for bad, good in bad_patterns:
        new_line = new_line.replace(bad, good)
    
    # 2. Fix the corrupted "from ... from ..." lines
    # Example: from src.brain.mcp.mcp_manager from src.brain.mcp import mcp_manager
    # regex to find "from src.brain... from src.brain..."
    new_line = re.sub(r'from src\.brain\.[a-zA-Z0-9_\.]+ from src\.brain\.', 'from src.brain.', new_line)
    
    # 3. Cleanup specific errors like "config_loader" in the wrong place
    new_line = new_line.replace('monitoring.config_loader', 'config.config_loader')
    new_line = new_line.replace('core.orchestration.logger', 'monitoring.logger')
    new_line = new_line.replace('core.server.logger', 'monitoring.logger')
    new_line = new_line.replace('mcp.logger', 'monitoring.logger')
    
    return new_line

def process_file(filepath):
    try:
        with open(filepath, encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        changed = False
        for line in lines:
            if 'src.brain' in line:
                fixed = fix_corrupted_line(line)
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

root_dir = '/Users/dev/Documents/GitHub/atlastrinity/src/brain'
files_updated = 0
for root, dirs, files in os.walk(root_dir):
    for file in files:
        if file.endswith('.py'):
            if process_file(os.path.join(root, file)):
                files_updated += 1

print(f"Surgically fixed {files_updated} files.")
