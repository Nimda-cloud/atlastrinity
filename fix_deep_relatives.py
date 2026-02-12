import os
import re

# Comprehensive map for relative-to-absolute modular realignment
DEEP_RELATIVE_MAP = {
    # Agents
    r'from \.agents\.atlas\b': 'from src.brain.agents.atlas',
    r'from \.agents\.tetyana\b': 'from src.brain.agents.tetyana',
    r'from \.agents\.grisha\b': 'from src.brain.agents.grisha',
    
    # Navigation
    r'from \.navigation\.tour_driver\b': 'from src.brain.navigation.tour_driver',
    r'from \.navigation\.map_state\b': 'from src.brain.navigation.map_state',
    r'from \.navigation\.tour_manager\b': 'from src.brain.navigation.tour_manager',
    
    # Monitoring -> Behavior (specifically for constraint_monitor)
    r'from \.monitoring\.constraint_monitor\b': 'from src.brain.behavior.constraint_monitor',
    
    # Core Server -> Voice
    r'from \.voice\.stt\b': 'from src.brain.voice.stt',
    r'from \.voice\.tts\b': 'from src.brain.voice.tts',
    
    # Core Server -> Services
    r'from \.services\.file_processor\b': 'from src.brain.services.file_processor',
    
    # Misplaced modular paths from previous sweeps
    'src.brain.behavior.agents.atlas': 'src.brain.agents.atlas',
    'src.brain.monitoring.constraint_monitor': 'src.brain.behavior.constraint_monitor',
    'src.brain.core.orchestration.agents.atlas': 'src.brain.agents.atlas',
    'src.brain.core.server.voice.stt': 'src.brain.voice.stt',
    'src.brain.core.server.services.file_processor': 'src.brain.services.file_processor',
    'src.brain.core.server.watchdog': 'src.brain.monitoring.watchdog',
}

def fix_deep_relative_imports():
    root_dir = '/Users/dev/Documents/GitHub/atlastrinity/'
    updated_count = 0
    
    # Scan the entire src directory for these specific broken patterns
    for r, d, files in os.walk(os.path.join(root_dir, 'src')):
        for file in files:
            if file.endswith('.py'):
                abs_path = os.path.join(r, file)
                with open(abs_path, encoding='utf-8') as f:
                    content = f.read()
                
                new_content = content
                for old_pattern, new_abs in DEEP_RELATIVE_MAP.items():
                    if old_pattern.startswith('from'):
                        new_content = re.sub(old_pattern, new_abs, new_content)
                    else:
                        new_content = new_content.replace(old_pattern, new_abs)

                if new_content != content:
                    with open(abs_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    updated_count += 1
                        
    print(f"Deep relative import fix complete. {updated_count} files updated.")

if __name__ == "__main__":
    fix_deep_relative_imports()
