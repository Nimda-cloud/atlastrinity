import re
from pathlib import Path


def clean_imports(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Skip non-Python files
    if not file_path.endswith(".py"):
        return False

    # Skip our own fix scripts
    if file_path.endswith(("fix_prints.py", "fix_logging.py", "fix_remaining_issues.py")):
        return False

    # Remove duplicate imports
    lines = content.split("\n")
    seen_imports = set()
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            cleaned_lines.append(line)
            continue

        # Handle import statements
        if stripped.startswith(("import ", "from ")):
            # Skip duplicate imports
            if stripped in seen_imports:
                continue
            seen_imports.add(stripped)

        cleaned_lines.append(line)

    # Rebuild content
    new_content = "\n".join(cleaned_lines)

    # Fix import order
    std_imports = []
    third_party_imports = []
    local_imports = []
    other_code = []

    in_imports = True
    current_imports = []

    for line in cleaned_lines:
        stripped = line.strip()

        if not in_imports:
            other_code.append(line)
            continue

        if not stripped or stripped.startswith("#"):
            current_imports.append(line)
            continue

        if stripped.startswith(("import ", "from ")):
            current_imports.append(line)
        else:
            in_imports = False
            other_code.append(line)

    # Sort imports
    for imp in current_imports:
        stripped = imp.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("from .") or stripped.startswith("from src."):
            local_imports.append(imp)
        elif any(
            pkg in stripped
            for pkg in ["os", "sys", "typing", "logging", "json", "pathlib", "time", "re"]
        ):
            std_imports.append(imp)
        elif stripped.startswith("import ") or stripped.startswith("from "):
            third_party_imports.append(imp)
        else:
            other_code.insert(0, imp)

    # Combine imports with newlines between groups
    all_imports = []

    if std_imports:
        all_imports.extend(std_imports)
        all_imports.append("")

    if third_party_imports:
        all_imports.extend(third_party_imports)
        all_imports.append("")

    if local_imports:
        all_imports.extend(local_imports)

    # Remove trailing newlines
    while all_imports and all_imports[-1].strip() == "":
        all_imports.pop()

    # Add a single newline after imports if there's code after
    if all_imports and other_code:
        all_imports.append("")

    # Rebuild file content
    new_content = "\n".join(all_imports + other_code)

    # Fix double newlines
    new_content = re.sub(r"\n{3,}", "\n\n", new_content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True


def main():
    # Get all Python files in the project
    python_files = []
    for ext in ["*.py"]:
        python_files.extend(Path(".").rglob(ext))

    # Fix imports in all Python files
    for file_path in python_files:
        try:
            if clean_imports(str(file_path)):
                print(f"Cleaned imports in {file_path}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    main()
