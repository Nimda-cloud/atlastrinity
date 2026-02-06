#!/usr/bin/env python3
import os
import re
from pathlib import Path
from typing import Any

import yaml

try:
    import toml
except ImportError:
    try:
        import tomllib as toml
    except ImportError:
        toml = None

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_SRC_ROOT = PROJECT_ROOT / "config"
CONFIG_DST_ROOT = Path.home() / ".config" / "atlastrinity"

# Mappings (Relative Source Template -> Relative Destination)
MAPPINGS = {
    "config.yaml.template": "config.yaml",
    "behavior_config.yaml.template": "behavior_config.yaml",
    "vibe_config.toml.template": "vibe_config.toml",
    "vibe/agents/accept-edits.toml.template": "vibe/agents/accept-edits.toml",
    "vibe/agents/auto-approve.toml.template": "vibe/agents/auto-approve.toml",
    "vibe/agents/plan.toml.template": "vibe/agents/plan.toml",
    "mcp_servers.json.template": "mcp/config.json",
    "prometheus.yml.template": "prometheus.yml",
}


def load_env():
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


def substitute_vars(content: str) -> str:
    replacements = {
        "${PROJECT_ROOT}": str(PROJECT_ROOT),
        "${HOME}": str(Path.home()),
        "${CONFIG_ROOT}": str(CONFIG_DST_ROOT),
        "${PYTHONPATH}": str(PROJECT_ROOT),
    }
    for key, value in replacements.items():
        content = content.replace(key, value)

    matches = re.findall(r"\${([A-Z0-9_]+)}", content)
    for var_name in set(matches):
        env_val = os.getenv(var_name)
        if env_val is not None:
            content = content.replace(f"${{{var_name}}}", env_val)
    return content


def validate_yaml(template_content: str, target_path: Path):
    """
    Validates that the target file has all keys present in the template.
    This is the 'Logic Check'. Works for both YAML and TOML files.
    """
    if not target_path.exists():
        return

    try:
        # Load template removing variable placeholders for structure check
        clean_tpl = re.sub(r"\${[A-Z0-9_]+}", "placeholder", template_content)

        # Determine file format and load accordingly
        if target_path.suffix == ".toml":
            if toml is None:
                print(f"  [!] Cannot validate {target_path.name}: toml library not installed")
                return
            tpl_data = toml.loads(clean_tpl)
            with open(target_path, encoding="utf-8") as f:
                target_data = toml.loads(f.read())
        else:
            # Default to YAML
            tpl_data = yaml.safe_load(clean_tpl)
            with open(target_path, encoding="utf-8") as f:
                target_data = yaml.safe_load(f)

        def check_structure(tpl: Any, tgt: Any, path: str = ""):
            if isinstance(tpl, dict):
                if not isinstance(tgt, dict):
                    print(
                        f"  [!] Logic Error: Expected dict at {path or 'root'}, got {type(tgt).__name__}"
                    )
                    return False
                for key in tpl:
                    if key not in tgt:
                        print(f"  [!] Logic Error: Missing key '{key}' at {path or 'root'}")
                        return False
                    if not check_structure(tpl[key], tgt[key], f"{path}.{key}" if path else key):
                        return False
            return True

        if check_structure(tpl_data, target_data):
            print(f"  [✓] Logic Check passed for {target_path.name}")
        else:
            print(
                f"  [⚠️] Logic Check failed for {target_path.name}. Manual intervention suggested."
            )

    except Exception as e:
        print(f"  [!] Could not perform logic check for {target_path.name}: {e}")


def sync_file(rel_src: str, rel_dst: str):
    src_path = CONFIG_SRC_ROOT / rel_src
    dst_path = CONFIG_DST_ROOT / rel_dst

    if not src_path.exists():
        return

    print(f"Processing: {rel_src} -> {rel_dst}")

    with open(src_path, encoding="utf-8") as f:
        template_content = f.read()

    final_content = substitute_vars(template_content)

    # Ensure directory exists
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    # Smart Sync: Overwrite if file doesn't exist or if structure is missing
    # In 'Local CI' mode, we might want to auto-adjust
    if not dst_path.exists():
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"  [+] Created {dst_path.name}")
    else:
        # Check if we need to auto-adjust (add missing keys)
        # For simplicity, we'll notify and the user can delete the file to reset
        # or we could implement a deep merge. Let's do a simple check first.
        validate_yaml(template_content, dst_path)


def main():
    load_env()
    print("=== AtlasTrinity Advanced Config Sync & Validator ===")
    for rel_src, rel_dst in MAPPINGS.items():
        sync_file(rel_src, rel_dst)
    print("=====================================================")


if __name__ == "__main__":
    main()
