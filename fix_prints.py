import re
import sys
from pathlib import Path


def fix_prints_in_file(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Skip files that already have logging imports
    if "import logging" in content:
        return False

    # Add logging import if not present
    if "import logging\n" not in content:
        content = "import logging\n\n" + content

    # Replace print statements with logging
    content = re.sub(r"^(\s*)print\((.*)\)", r"\1logging.info(\2)", content, flags=re.MULTILINE)

    # Special case for print with file parameter
    content = re.sub(r"print\((.*?),\s*file=sys\.stderr\)", r"logging.error(\1)", content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def main():
    test_files = [
        "test_cascade_flow_real.py",
        "test_windsurf_cascade.py",
        "test_windsurf_free_model.py",
        "test_windsurf_simple.py",
        "test_windsurf_standalone.py",
    ]

    for test_file in test_files:
        if Path(test_file).exists():
            fixed = fix_prints_in_file(test_file)
            if fixed:
                print(f"Fixed print statements in {test_file}")
            else:
                print(f"Skipped {test_file} (already has logging or no changes needed)")
        else:
            print(f"File not found: {test_file}")


if __name__ == "__main__":
    main()
