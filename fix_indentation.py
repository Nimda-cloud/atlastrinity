import re
from pathlib import Path


def fix_file(file_path):
    with open(file_path, encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and fix indented imports
    in_imports = False
    fixed_lines = []
    imports = []
    
    for line in lines:
        stripped = line.strip()
        
        # Check if this is an import line
        if stripped.startswith(('import ', 'from ')) and not stripped.startswith('from pathlib'):
            if not in_imports:
                in_imports = True
            imports.append(line)
        else:
            if in_imports:
                # Add all collected imports at the current position
                fixed_lines.extend(sorted(imports, key=lambda x: (not x.startswith('from '), x.lower())))
                imports = []
                in_imports = False
            fixed_lines.append(line)
    
    # If we still have imports at the end, add them
    if imports:
        fixed_lines.extend(sorted(imports, key=lambda x: (not x.startswith('from '), x.lower())))
    
    # Write the fixed content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)

def main():
    files_to_fix = [
        'test_windsurf_simple.py',
        'test_windsurf_standalone.py'
    ]
    
    for file_name in files_to_fix:
        if Path(file_name).exists():
            fix_file(file_name)
            print(f"Fixed imports in {file_name}")
        else:
            print(f"File not found: {file_name}")

if __name__ == "__main__":
    main()
