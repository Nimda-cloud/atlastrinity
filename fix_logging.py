import re
import sys
from pathlib import Path


def fix_file(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Add logger setup at the top of the file
    logger_setup = """import logging
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

    # Skip if already has logger setup
    if "logger = logging.getLogger(" in content:
        return False

    # Add logger setup after imports
    content = re.sub(
        r"^(import .+?\n)(?=from|$)",
        r"\1\n" + logger_setup,
        content,
        flags=re.DOTALL | re.MULTILINE,
    )

    # Replace all logging.info with logger.info
    content = content.replace("logging.info(", "logger.info(")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return True


def fix_imports(file_path):
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # Move all imports to the top
    imports = set()
    lines = content.split("\n")
    new_lines = []

    # First pass: collect all imports
    for line in lines:
        if line.strip().startswith(("import ", "from ")):
            imports.add(line)
        else:
            new_lines.append(line)

    # If no imports found, return original content
    if not imports:
        return content

    # Rebuild content with imports at the top
    new_content = "\n".join(sorted(imports, key=lambda x: (not x.startswith("from "), x.lower())))
    new_content += "\n\n" + "\n".join([line for line in new_lines if line.strip()])

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

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
            fixed_logging = fix_file(test_file)
            fixed_imports = fix_imports(test_file)

            if fixed_logging or fixed_imports:
                print(f"Fixed {test_file}")
            else:
                print(f"Skipped {test_file} (no changes needed)")
        else:
            print(f"File not found: {test_file}")


if __name__ == "__main__":
    main()
