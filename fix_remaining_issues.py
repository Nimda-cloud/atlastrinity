import re
from pathlib import Path


def fix_file(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Fix indentation issues
    content = re.sub(r"^    from ", "from ", content, flags=re.MULTILINE)
    content = re.sub(r"^    import ", "import ", content, flags=re.MULTILINE)

    # Replace print statements with logging
    if "import logging" not in content:
        logging_setup = """import logging
import os
import sys
from pathlib import Path

# Set up logger
logger = logging.getLogger(Path(__file__).stem)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

"""
        # Add after first import block
        content = re.sub(
            r"^(import .+?\n)(?=from|$)",
            r"\1\n" + logging_setup,
            content,
            flags=re.DOTALL | re.MULTILINE,
        )

    # Replace print statements
    content = re.sub(r"^(\s*)print\((.*)\)", r"\1logger.info(\2)", content, flags=re.MULTILINE)

    # Special case for print to stderr
    content = re.sub(r"print\((.*?),\s*file=sys\.stderr\)", r"logger.error(\1)", content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def fix_type_aliases(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Update type alias to use | syntax
    content = content.replace(
        "ContentItem = Union[str, dict[str, Any]]", "ContentItem = str | dict[str, Any]"
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def main():
    # Fix test files with indentation issues
    test_files = ["test_windsurf_simple.py", "test_windsurf_standalone.py"]

    for file_name in test_files:
        if Path(file_name).exists():
            fix_file(file_name)
            print(f"Fixed {file_name}")
        else:
            print(f"File not found: {file_name}")

    # Fix print statements in other files
    other_files = ["standalone_windsurf_test.py", "test_cascade_flow.py"]

    for file_name in other_files:
        if Path(file_name).exists():
            fix_file(file_name)
            print(f"Fixed {file_name}")
        else:
            print(f"File not found: {file_name}")

    # Fix type aliases
    if Path("providers/windsurf.py").exists():
        fix_type_aliases("providers/windsurf.py")
        print("Fixed type aliases in providers/windsurf.py")


if __name__ == "__main__":
    main()
