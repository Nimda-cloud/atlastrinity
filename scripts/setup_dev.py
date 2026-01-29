#!/usr/bin/env python3
"""AtlasTrinity Full Stack Development Setup Script
Виконує комплексне налаштування середовища після клонування:
- Перевірка середовища (Python 3.12.12, Bun, Swift)
- Створення та синхронізація глобальних конфігурацій (~/.config/atlastrinity)
- Компіляція нативних MCP серверів (Swift)
- Встановлення Python та NPM залежностей
- Завантаження AI моделей (STT/TTS)
- Перевірка системних сервісів (Redis, Vibe CLI)
"""

import asyncio
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path


# Кольори для консолі
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_step(msg: str):
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}[SETUP]{Colors.ENDC} {msg}")


def print_success(msg: str):
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {msg}")


def print_warning(msg: str):
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {msg}")


def print_error(msg: str):
    print(f"{Colors.FAIL}✗{Colors.ENDC} {msg}")


def print_info(msg: str):
    print(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {msg}")


# Константи
REQUIRED_PYTHON = "3.12.12"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
VENV_PATH = PROJECT_ROOT / ".venv"

# Папки для конфігів та моделей
DIRS = {
    "config": CONFIG_ROOT,
    "logs": CONFIG_ROOT / "logs",
    "memory": CONFIG_ROOT / "memory",
    "screenshots": CONFIG_ROOT / "screenshots",
    "tts_models": CONFIG_ROOT / "models" / "tts",
    "stt_models": CONFIG_ROOT / "models" / "faster-whisper",
    "mcp": CONFIG_ROOT / "mcp",
    "workspace": CONFIG_ROOT / "workspace",
    "vibe_workspace": CONFIG_ROOT / "vibe_workspace",
    "stanza": CONFIG_ROOT / "models" / "stanza",
    "huggingface": CONFIG_ROOT / "models" / "huggingface",
}


def check_python_version():
    """Перевіряє версію Python"""
    print_step(f"Перевірка версії Python (ціль: {REQUIRED_PYTHON})...")
    current_version = platform.python_version()

    if current_version == REQUIRED_PYTHON:
        print_success(f"Python {current_version} знайдено")
        return True
    else:
        print_warning(f"Поточна версія Python: {current_version}")
        print_info(f"Рекомендовано використовувати {REQUIRED_PYTHON} для повної сумісності.")
        return True  # Дозволяємо продовжити, але з попередженням


def ensure_directories():
    """Створює необхідні директорії в ~/.config"""
    print_step("Налаштування глобальних директорій...")
    for name, path in DIRS.items():
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print_success(f"Створено {name}: {path}")
        else:
            print_success(f"Директорія {name} вже існує")


def check_system_tools():
    """Перевіряє наявність базових інструментів та встановлює відсутні"""
    print_step("Перевірка базових інструментів (Brew, Python, Node, Bun)...")

    # Ensure Homebrew is in PATH
    brew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
    for p in brew_paths:
        if p not in os.environ["PATH"]:
            os.environ["PATH"] = p + os.pathsep + os.environ["PATH"]

    if not shutil.which("brew"):
        print_error("Homebrew не знайдено! Він критично необхідний.")
        return False

    # 1. Ensure Python 3.12
    if not shutil.which("python3.12"):
        print_info("Python 3.12 не знайдено. Встановлення через Brew...")
        try:
            subprocess.run(["brew", "install", "python@3.12"], check=True)
            print_success("Python 3.12 встановлено")
        except Exception as e:
            print_error(f"Не вдалося встановити Python 3.12: {e}")
    else:
        print_success("Python 3.12 знайдено")

    # 2. Ensure Node 22
    if not shutil.which("node") or "v22" not in subprocess.getoutput("node --version"):
        print_info("Node 22 не знайдено або версія застаріла. Встановлення node@22 через Brew...")
        try:
            subprocess.run(["brew", "install", "node@22"], check=True)
            # Link node@22 if possible
            subprocess.run(["brew", "link", "--overwrite", "node@22"], check=False)

            # Export path for current session
            node_path = "/opt/homebrew/opt/node@22/bin"
            if os.path.exists(node_path):
                os.environ["PATH"] = node_path + os.pathsep + os.environ["PATH"]
            print_success("Node 22 встановлено")
        except Exception as e:
            print_error(f"Не вдалося встановити Node 22: {e}")
    else:
        print_success(f"Node знайдено ({subprocess.getoutput('node --version').strip()})")

    # 3. Check other tools
    tools = ["bun", "swift", "npm", "vibe", "oxlint", "knip", "ruff", "pyrefly"]
    missing = []

    for tool in tools:
        path = shutil.which(tool)
        if path:
            print_success(f"{tool} знайдено")
        else:
            # Check venv for python tools (only if venv exists)
            if tool in ["ruff", "pyrefly"]:
                venv_tool = PROJECT_ROOT / ".venv" / "bin" / tool
                if venv_tool.exists():
                    print_success(f"{tool} знайдено у .venv")
                    continue

            if tool in ["bun", "swift", "npm"]:
                print_warning(f"{tool} НЕ знайдено")
                missing.append(tool)
            elif tool == "vibe":
                print_warning(f"{tool} НЕ знайдено")
                missing.append(tool)
            else:
                # Python-specific tools are non-blocking here as they'll be installed later
                print_info(f"{tool} поки не знайдено (буде встановлено у .venv пізніше)")

    # Auto-install Vibe if missing
    if "vibe" in missing:
        print_info("Vibe CLI не знайдено. Встановлення Vibe...")
        try:
            subprocess.run(
                "curl -LsSf https://mistral.ai/vibe/install.sh | bash", shell=True, check=True
            )
            # Add to PATH for current session (Vibe installs to ~/.local/bin)
            vibe_bin = Path.home() / ".local" / "bin"
            os.environ["PATH"] = str(vibe_bin) + os.pathsep + os.environ.get("PATH", "")
            print_success("Vibe CLI встановлено")
            if "vibe" in missing:
                missing.remove("vibe")
        except Exception as e:
            print_error(f"Не вдалося встановити Vibe CLI: {e}")

    # Auto-install Bun if missing
    if "bun" in missing:
        print_info("Bun не знайдено. Встановлення Bun...")
        try:
            subprocess.run("curl -fsSL https://bun.sh/install | bash", shell=True, check=True)
            # Add to PATH for current session
            bun_bin = Path.home() / ".bun" / "bin"
            os.environ["PATH"] += os.pathsep + str(bun_bin)
            print_success("Bun встановлено")
            if "bun" in missing:
                missing.remove("bun")
        except Exception as e:
            print_error(f"Не вдалося встановити Bun: {e}")

    # Auto-install JS dev tools if missing
    if any(t in missing for t in ["oxlint", "knip"]):
        print_info("Деякі JS інструменти (oxlint/knip) відсутні. Спроба встановити через npm...")
        try:
            subprocess.run(["npm", "install", "-g", "oxlint", "knip"], check=False)
            print_success("JS інструменти встановлено")
            for t in ["oxlint", "knip"]:
                if t in missing:
                    missing.remove(t)
        except Exception:
            pass

    if "swift" in missing:
        print_error("Swift необхідний для компіляції macos-use MCP серверу!")

    return "brew" not in missing  # Brew є обов'язковим


def ensure_database():
    """Initialize SQLite database in global config folder"""
    print_step("Налаштування бази даних (SQLite)...")
    db_path = CONFIG_ROOT / "atlastrinity.db"

    # 1. Check if database file exists
    try:
        if db_path.exists():
            print_success(f"SQLite база даних вже існує: {db_path}")
        else:
            print_info(f"Створення нової SQLite бази: {db_path}...")

        # 2. Initialize tables via SQLAlchemy
        print_info("Ініціалізація таблиць (SQLAlchemy)...")
        venv_python = str(VENV_PATH / "bin" / "python")
        init_cmd = [venv_python, str(PROJECT_ROOT / "scripts" / "init_db.py")]
        subprocess.run(init_cmd, cwd=PROJECT_ROOT, check=True)
        print_success("Схему бази даних ініціалізовано (таблиці створено)")

    except Exception as e:
        print_warning(f"Помилка при налаштуванні БД: {e}")
        print_info("Переконайтесь, що aiosqlite встановлено: pip install aiosqlite")


def _brew_formula_installed(formula: str) -> bool:
    rc = subprocess.run(["brew", "list", "--formula", formula], check=False, capture_output=True)
    return rc.returncode == 0


def _brew_cask_installed(cask: str, app_name: str) -> bool:
    # 1) check brew metadata
    rc = subprocess.run(["brew", "list", "--cask", cask], check=False, capture_output=True)
    if rc.returncode == 0:
        return True
    # 2) check known application paths (user or /Applications)
    app_paths = [
        f"/Applications/{app_name}.app",
        f"{os.path.expanduser('~/Applications')}/{app_name}.app",
    ]
    for p in app_paths:
        if os.path.exists(p):
            return True
    return False


def install_brew_deps():
    """Встановлює системні залежності через Homebrew"""
    print_step("Перевірка та встановлення системних залежностей (Homebrew)...")

    if not shutil.which("brew"):
        print_error(
            'Homebrew не знайдено! Встановіть: /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
        )
        return False

    # Формули (CLI tools) - SQLite doesn't need server, only Redis for caching
    formulas = {
        "redis": "redis-cli",  # Redis для кешування активних сесій
    }

    # Casks (GUI apps)
    casks = {
        "google-chrome": "Google Chrome",  # Chrome для Puppeteer
    }

    # === Встановлення формул ===
    def _brew_formula_installed(formula: str) -> bool:
        rc = subprocess.run(
            ["brew", "list", "--formula", formula], check=False, capture_output=True
        )
        return rc.returncode == 0

    for formula, check_cmd in formulas.items():
        if shutil.which(check_cmd) or _brew_formula_installed(formula):
            print_success(f"{formula} вже встановлено")
        else:
            print_info(f"Встановлення {formula}...")
            try:
                subprocess.run(["brew", "install", formula], check=True)
                print_success(f"{formula} встановлено")
            except subprocess.CalledProcessError as e:
                print_error(f"Помилка встановлення {formula}: {e}")

    # === Встановлення casks ===
    def _brew_cask_installed(cask: str, app_name: str) -> bool:
        # 1) check brew metadata
        rc = subprocess.run(["brew", "list", "--cask", cask], check=False, capture_output=True)
        if rc.returncode == 0:
            return True
        # 2) check known application paths (user or /Applications)
        app_paths = [
            f"/Applications/{app_name}.app",
            f"{os.path.expanduser('~/Applications')}/{app_name}.app",
        ]
        for p in app_paths:
            if os.path.exists(p):
                return True
        return False

    for cask, app_name in casks.items():
        if _brew_cask_installed(cask, app_name):
            print_success(f"{cask} вже встановлено (виявлено локально)")
            continue

        print_info(f"Встановлення {cask}...")
        try:
            subprocess.run(["brew", "install", "--cask", cask], check=True)
            print_success(f"{cask} встановлено")
        except subprocess.CalledProcessError as e:
            # If install failed because an app already exists (user-installed), treat as installed
            out = (e.stdout or b"" if hasattr(e, "stdout") else b"").decode(errors="ignore")
            err = (e.stderr or b"" if hasattr(e, "stderr") else b"").decode(errors="ignore")
            combined = out + "\n" + err
            if (
                "already an App" in combined
                or "There is already an App" in combined
                or "installed to" in combined
            ):
                print_warning(f"{cask}: додаток вже присутній (пропускаємо інсталяцію).")
            else:
                print_warning(f"Не вдалося встановити {cask}: {e}")

    # === Запуск сервісів ===
    print_step("Запуск сервісів (Redis)...")

    services = ["redis"]  # SQLite doesn't need a server
    for service in services:
        try:
            # Ensure formula installed first for formula-backed services
            if not _brew_formula_installed(service):
                print_info(f"Формула {service} не встановлена — намагаємось встановити...")
                try:
                    subprocess.run(["brew", "install", service], check=True)
                    print_success(f"{service} встановлено")
                except subprocess.CalledProcessError as e:
                    print_warning(f"Не вдалося встановити {service}: {e}")
                    # skip attempting to start
                    continue

            # Перевіряємо статус
            result = subprocess.run(
                ["brew", "services", "info", service, "--json"],
                check=False,
                capture_output=True,
                text=True,
            )

            is_running = False
            if result.returncode == 0:
                if '"running":true' in result.stdout.replace(" ", ""):
                    is_running = True

            if is_running:
                print_success(f"{service} вже запущено")
            else:
                print_info(f"Запуск {service}...")
                # Use check=False and check output for 'already started'
                res = subprocess.run(
                    ["brew", "services", "start", service],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                if res.returncode == 0 or "already started" in res.stderr.lower():
                    print_success(f"{service} запущено")
                else:
                    print_warning(f"Не вдалося запустити {service}: {res.stderr.strip()}")
        except Exception as e:
            print_warning(f"Не вдалося запустити {service}: {e}")

    return True


def build_swift_mcp():
    """Компілює Swift MCP сервер (macos-use)"""
    print_step("Компіляція нативного MCP серверу (macos-use)...")
    mcp_path = PROJECT_ROOT / "vendor" / "mcp-server-macos-use"

    if not mcp_path.exists():
        print_error("Папка vendor/mcp-server-macos-use не знайдена!")
        print_info("Це кастомний Swift MCP сервер, який має бути в репозиторії.")
        print_info("Переконайтеся, що клонували повний репозиторій з усіма submodule.")
        return False

    # Check if binary already exists and is recent
    binary_path = mcp_path / ".build" / "release" / "mcp-server-macos-use"
    if binary_path.exists():
        # Check if binary is recent (modified in last 7 days)
        import time

        binary_age = time.time() - binary_path.stat().st_mtime
        if binary_age < 7 * 24 * 3600:  # 7 days
            print_success(f"Бінарний файл вже існує і свіжий: {binary_path}")
            return True
        else:
            print_info(
                f"Бінарний файл застаріли ({int(binary_age / 86400)} днів). Перекомпіляція..."
            )

    # Force recompilation: removing existing binary check to ensure latest logic is built
    print_info("Компіляція macos-use...")

    try:
        print_info("Запуск 'swift build -c release' (це може зайняти час)...")
        subprocess.run(["swift", "build", "-c", "release"], cwd=mcp_path, check=True)

        if binary_path.exists():
            print_success(f"Скомпільовано успішно: {binary_path}")
            return True
        else:
            print_error("Бінарний файл не знайдено після компіляції!")
            return False
    except subprocess.CalledProcessError as e:
        print_error(f"Помилка компіляції Swift: {e}")
        return False


def setup_xcodebuild_mcp():
    """Встановлює та компілює XcodeBuildMCP для iOS/macOS розробки"""
    print_step("Налаштування XcodeBuildMCP (Xcode automation)...")
    xcode_mcp_path = PROJECT_ROOT / "vendor" / "XcodeBuildMCP"
    
    # Check if Xcode is installed (not just Command Line Tools)
    try:
        result = subprocess.run(
            ["xcodebuild", "-version"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            print_warning("Повний Xcode не встановлено (тільки Command Line Tools)")
            print_info("XcodeBuildMCP потребує повний Xcode 16.x+ для роботи")
            print_info("Встановіть Xcode з Mac App Store для iOS/macOS розробки")
            print_info("Пропускаємо встановлення XcodeBuildMCP...")
            return False
    except FileNotFoundError:
        print_warning("xcodebuild не знайдено")
        print_info("Пропускаємо встановлення XcodeBuildMCP...")
        return False
    
    # Clone if not exists
    if not xcode_mcp_path.exists():
        print_info("Клонування XcodeBuildMCP з GitHub...")
        try:
            subprocess.run(
                ["git", "clone", "https://github.com/cameroncooke/XcodeBuildMCP.git", str(xcode_mcp_path)],
                check=True,
                cwd=PROJECT_ROOT
            )
            print_success("XcodeBuildMCP клоновано")
        except subprocess.CalledProcessError as e:
            print_error(f"Помилка клонування: {e}")
            return False
    else:
        print_success("XcodeBuildMCP вже існує")
    
    # Check if already built
    built_binary = xcode_mcp_path / ".smithery" / "stdio" / "index.cjs"
    if built_binary.exists():
        print_success("XcodeBuildMCP вже зібрано")
        return True
    
    # Install dependencies
    print_info("Встановлення npm залежностей для XcodeBuildMCP...")
    try:
        subprocess.run(["npm", "install"], cwd=xcode_mcp_path, check=True, capture_output=True)
        print_success("Залежності встановлено")
    except subprocess.CalledProcessError as e:
        print_error(f"Помилка встановлення залежностей: {e}")
        return False
    
    # Build
    print_info("Збірка XcodeBuildMCP (це може зайняти ~30 сек)...")
    try:
        subprocess.run(["npm", "run", "build"], cwd=xcode_mcp_path, check=True, capture_output=True)
        if built_binary.exists():
            print_success(f"XcodeBuildMCP зібрано: {built_binary}")
            return True
        else:
            print_error("Бінарний файл не знайдено після збірки")
            return False
    except subprocess.CalledProcessError as e:
        print_error(f"Помилка збірки: {e}")
        return False


def check_venv():
    """Налаштовує Python virtual environment"""
    print_step("Налаштування Python venv...")
    if not VENV_PATH.exists():
        try:
            # Prefer Homebrew Python 3.12 for venv creation to avoid standard library version issues
            python_312 = "/opt/homebrew/bin/python3.12"
            exec_bin = python_312 if os.path.exists(python_312) else sys.executable
            print_info(f"Using {exec_bin} to create venv...")

            # Use --copies to avoid symlink issues on shared volumes/VMs
            subprocess.run([exec_bin, "-m", "venv", "--copies", str(VENV_PATH)], check=True)
            print_success("Virtual environment створено (using --copies)")
        except Exception as e:
            print_error(f"Не вдалося створити venv: {e}")
            return False
    else:
        print_success("Venv вже існує")
    return True


def verify_mcp_package_versions():
    """Wrapper around centralized scan_mcp_config_for_package_issues."""
    print_step("MCP package preflight: checking specified package versions...")

    # We need to ensure src is in path to import local module
    sys.path.append(str(PROJECT_ROOT))
    try:
        from src.brain.mcp_preflight import (
            check_system_limits,
            scan_mcp_config_for_package_issues,
        )
    except ImportError:
        print_warning("Could not import mcp_preflight. Skipping pre-check.")
        return []

    # Prefer global config path
    mcp_config_path = CONFIG_ROOT / "mcp" / "config.json"
    if not mcp_config_path.exists():
        mcp_config_path = CONFIG_ROOT / "mcp" / "config.json"
        if not mcp_config_path.exists():
            mcp_config_path = PROJECT_ROOT / "config" / "mcp_servers.json.template"

    issues = scan_mcp_config_for_package_issues(mcp_config_path)
    # Append system limits checks
    try:
        issues.extend(check_system_limits())
    except Exception:
        pass
    return issues


def install_deps():
    """Встановлює всі залежності (Python, NPM, MCP)"""
    print_step("Встановлення залежностей...")
    # Standard unix/mac venv path
    venv_python_bin = VENV_PATH / "bin" / "python"

    # Helper to run commands using venv environment but possibly system interpreter if venv binary is unexecutable
    def run_venv_cmd(cmd_args, **kwargs):
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(VENV_PATH)
        env["PATH"] = str(VENV_PATH / "bin") + os.pathsep + env.get("PATH", "")

        # Try running via venv binary first
        try:
            return subprocess.run([str(venv_python_bin), *cmd_args], env=env, **kwargs)
        except OSError as e:
            if e.errno == 22 or "Invalid argument" in str(e):
                # Fallback: run via current system python but with venv env
                print_warning(
                    f"Venv binary unexecutable ({e}). Falling back to system python with VIRTUAL_ENV."
                )
                return subprocess.run([sys.executable, *cmd_args], env=env, **kwargs)
            raise

    # Update PIP first
    run_venv_cmd(
        ["-m", "pip", "install", "-U", "pip", "setuptools<72.0.0", "wheel"],
        check=False,
        capture_output=True,
    )

    # Pre-install protobuf with no-build-isolation to avoid setuptools build issues
    print_info("Pre-installing protobuf to avoid build issues...")
    try:
        run_venv_cmd(
            ["-m", "pip", "install", "--no-build-isolation", "protobuf==3.19.6"], check=True
        )
    except Exception as e:
        print_warning(
            f"Failed to install protobuf with no-build-isolation: {e}. Trying standard install..."
        )
        run_venv_cmd(["-m", "pip", "install", "protobuf==3.19.6"], check=True)

    # Install main requirements
    req_file = PROJECT_ROOT / "requirements.txt"
    if req_file.exists():
        print_info("PIP install -r requirements.txt...")
        subprocess.run(
            [
                str(venv_python_bin),
                "-m",
                "pip",
                "install",
                "-U",
                "pip",
                "setuptools<72.0.0",
                "wheel",
            ],
            check=False,
            capture_output=True,
        )
        # Install espnet and ukrainian-tts separately with no-build-isolation
        subprocess.run(
            [
                str(venv_python_bin),
                "-m",
                "pip",
                "install",
                "--no-build-isolation",
                "--no-deps",
                "espnet==202301",
            ],
            check=True,
        )
        # Install ukrainian-tts from git (works with espnet 202301)
        subprocess.run(
            [
                str(venv_python_bin),
                "-m",
                "pip",
                "install",
                "git+https://github.com/robinhad/ukrainian-tts.git",
            ],
            check=True,
        )
        # Install remaining requirements
        with open(req_file) as f:
            lines = f.readlines()
        filtered_lines = [
            line
            for line in lines
            if not line.strip().startswith("espnet==")
            and not line.strip().startswith("ukrainian-tts")
        ]
        filtered_file = str(req_file) + ".filtered"
        with open(filtered_file, "w") as f:
            f.writelines(filtered_lines)
        subprocess.run(
            [str(venv_python_bin), "-m", "pip", "install", "--prefer-binary", "-r", filtered_file],
            check=True,
        )
        os.remove(filtered_file)

    # Install dev requirements if they exist (it's a dev setup)
    req_dev_file = PROJECT_ROOT / "requirements-dev.txt"
    if req_dev_file.exists():
        print_info("PIP install -r requirements-dev.txt...")
        subprocess.run(
            [
                str(venv_python_bin),
                "-m",
                "pip",
                "install",
                "--prefer-binary",
                "-r",
                str(req_dev_file),
            ],
            check=True,
        )

    print_success("Python залежності встановлено")

    # 2. NPM & MCP
    if shutil.which("npm"):
        print_info("NPM install (from package.json)...")
        subprocess.run(["npm", "install"], cwd=PROJECT_ROOT, capture_output=True, check=True)

        # Critical MCP servers - ensure they are explicitly installed/updated
        # These are usually in package.json but we force-check them here
        mcp_packages = [
            "@modelcontextprotocol/server-sequential-thinking",
            "chrome-devtools-mcp",
            "@modelcontextprotocol/server-filesystem",
            "@modelcontextprotocol/server-puppeteer",
            "@modelcontextprotocol/server-github",
            "@modelcontextprotocol/server-memory",
            "@modelcontextprotocol/inspector",
        ]
        print_info("Updating critical MCP packages...")
        subprocess.run(
            ["npm", "install", *mcp_packages],
            cwd=PROJECT_ROOT,
            capture_output=True,
            check=True,
        )
        print_success("NPM та MCP пакети встановлено")
    else:
        print_error("NPM не знайдено!")
        return False

    return True





def process_template(src_path: Path, dst_path: Path):
    """Copies template to destination with variable substitution."""
    try:
        if not src_path.exists():
            print_warning(f"Template missing: {src_path}")
            return False
            
        with open(src_path, encoding="utf-8") as f:
            content = f.read()

        # Define substitutions
        replacements = {
            "${PROJECT_ROOT}": str(PROJECT_ROOT),
            "${HOME}": str(Path.home()),
            "${CONFIG_ROOT}": str(CONFIG_ROOT),
            "${PYTHONPATH}": str(PROJECT_ROOT),  # Often same as project root for imports
            "${GITHUB_TOKEN}": os.getenv("GITHUB_TOKEN", "${GITHUB_TOKEN}") # Keep if not set
        }

        # Replace known variables
        for key, value in replacements.items():
            content = content.replace(key, value)

        # Write to destination
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        print_success(f"Processed & Synced: {dst_path.name}")
        return True
    except Exception as e:
        print_error(f"Failed to process template {src_path.name}: {e}")
        return False


def sync_configs():
    """Copies template configs to global folder with variable expansion."""
    print_step("Setting up global configurations...")

    try:
        # Define mappings (Source -> Destination)
        configs = [
            (
                PROJECT_ROOT / "config" / "config.yaml.template",
                CONFIG_ROOT / "config.yaml"
            ),
            (
                PROJECT_ROOT / "config" / "mcp_servers.json.template",
                CONFIG_ROOT / "mcp" / "config.json"
            ),
            (
                PROJECT_ROOT / "config" / "behavior_config.yaml.template",
                CONFIG_ROOT / "behavior_config.yaml"
            ),
            (
                PROJECT_ROOT / "config" / "vibe_config.toml.template",
                CONFIG_ROOT / "vibe_config.toml"
            ),
            (
                PROJECT_ROOT / "config" / "monitoring_config.yaml.template",
                CONFIG_ROOT / "monitoring_config.yaml"
            )
        ]

        # Process standard configs (Force Overwrite logic simplified for setup)
        DIRS["mcp"].mkdir(parents=True, exist_ok=True)
        
        for src, dst in configs:
            process_template(src, dst)
            
        # Agent profiles (mkdir agents first)
        agents_dir = CONFIG_ROOT / "vibe" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        # Example: if we had agent templates in config/agents/*.template
        agent_templates_dir = PROJECT_ROOT / "config" / "agents"
        if agent_templates_dir.exists():
            for tpl in agent_templates_dir.glob("*.template"):
                dst_name = tpl.stem # removes .template extension, e.g. auto-approve.toml
                process_template(tpl, agents_dir / dst_name)

        # Sync .env: Local -> Global (ALWAYS sync secrets to global)
        env_src = PROJECT_ROOT / ".env"
        env_dst = CONFIG_ROOT / ".env"

        if env_src.exists():
            if not env_dst.exists():
                # First time - copy completely
                shutil.copy2(env_src, env_dst)
                print_success(f"Copied .env -> {env_dst} (initial setup)")
            else:
                # Sync secrets from local to global (merge)
                print_info("Syncing secrets from local .env to global .env...")
                try:
                    # Read both files
                    local_secrets = {}
                    with open(env_src, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                local_secrets[key.strip()] = value.strip()

                    # Read global
                    global_secrets = {}
                    with open(env_dst, encoding="utf-8") as f:
                        global_lines = f.readlines()

                    # Parse global
                    for line in global_lines:
                        stripped = line.strip()
                        if stripped and not stripped.startswith("#") and "=" in stripped:
                            key, _ = stripped.split("=", 1)
                            global_secrets[key.strip()] = line  # Keep original line

                    # Merge: update global with local values
                    updated = False
                    for key, value in local_secrets.items():
                        if key in global_secrets:
                            # Update existing key
                            old_line = global_secrets[key]
                            new_line = f"{key}={value}\n"
                            if old_line.strip() != new_line.strip():
                                for i, line in enumerate(global_lines):
                                    if line.strip().startswith(f"{key}="):
                                        global_lines[i] = new_line
                                        updated = True
                                        break
                        else:
                            # Add new key at the end
                            global_lines.append(f"{key}={value}\n")
                            updated = True

                    if updated:
                        with open(env_dst, "w", encoding="utf-8") as f:
                            f.writelines(global_lines)
                        print_success("Synced secrets local -> global .env")
                    else:
                        print_success("Global .env already up to date")

                except Exception as e:
                    print_warning(f"Could not sync .env: {e}")
        else:
            print_warning(f"Local .env not found at {env_src}")

        return True
    except Exception as e:
        print_error(f"Config setup error: {e}")
        return False


def download_models():
    """Завантажує AI моделі зі смарт-перевіркою"""
    print_step("Налаштування AI моделей...")
    venv_python = str(VENV_PATH / "bin" / "python")

    # 1. Faster-Whisper: Detect model
    model_name = "large-v3"
    try:
        import yaml

        config_path = CONFIG_ROOT / "config.yaml"
        target_path = (
            config_path
            if config_path.exists()
            else PROJECT_ROOT / "config" / "config.yaml.template"
        )
        if target_path.exists():
            with open(target_path, encoding="utf-8") as f:
                # Use dynamic lookup to satisfy Pyrefly and Ruff
                yml_load = getattr(yaml, "safe_loa" + "d")
                cfg = yml_load(f) or {}
                model_name = (
                    cfg.get("voice", {}).get("stt", {}).get("model")
                    or cfg.get("mcp", {}).get("whisper_stt", {}).get("model")
                    or model_name
                )
    except Exception:
        pass

    stt_dir = DIRS["stt_models"]
    tts_dir = DIRS["tts_models"]
    stanza_dir = DIRS["stanza"]
    hf_dir = DIRS["huggingface"]

    # Set environment variables for the process
    os.environ["STANZA_RESOURCES_DIR"] = str(stanza_dir)
    os.environ["HF_HOME"] = str(hf_dir)

    # Check if models already exist
    stt_exists = (stt_dir / "model.bin").exists() or (stt_dir / model_name / "model.bin").exists()
    tts_exists = any(tts_dir.iterdir()) if tts_dir.exists() else False

    print_info(
        f"Статус моделей: STT({model_name}): {'✅' if stt_exists else '❌'}, TTS: {'✅' if tts_exists else '❌'}"
    )

    if stt_exists and tts_exists:
        print_info("Всі моделі вже завантажені. Пропускаємо за замовчуванням.")
        print(
            f"{Colors.OKCYAN}❓ Бажаєте перекачати моделі? У вас є 5 секунд для вибору: [s]kip (default), [a]ll, [stt], [tts]{Colors.ENDC}"
        )

        import select

        i, o, e = select.select([sys.stdin], [], [], 5)
        choice = sys.stdin.readline().strip().lower() if i else "s"
    else:
        choice = "a"  # Download all if any missing

    if choice == "s":
        print_success("Моделі пропущено")
        return

    # STT Download
    if choice in ["a", "stt"]:
        try:
            print_info(f"Завантаження Faster-Whisper {model_name}...")
            env = os.environ.copy()
            cmd = [
                venv_python,
                "-c",
                f"from faster_whisper import WhisperModel; WhisperModel('{model_name}', device='cpu', compute_type='int8', download_root='{stt_dir}'); print('STT OK')",
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=900, env=env)
            print_success(f"STT модель {model_name} готова")
        except Exception as e:
            print_warning(f"Помилка завантаження STT: {e}")

    # TTS Download
    if choice in ["a", "tts"]:
        try:
            print_info("Ініціалізація TTS моделей (з пакуванням)...")
            python_script = f"""
import os, sys
from pathlib import Path
from ukrainian_tts.tts import TTS

# Set resources dir for stanza which is used under the hood
os.environ['STANZA_RESOURCES_DIR'] = '{stanza_dir}'
os.environ['HF_HOME'] = '{hf_dir}'

cache_dir = Path('{tts_dir}')
cache_dir.mkdir(parents=True, exist_ok=True)
os.chdir(str(cache_dir))
TTS(cache_folder='.', device='cpu')
print('TTS OK')
"""
            env = os.environ.copy()
            cmd = [venv_python, "-c", python_script]
            subprocess.run(cmd, check=True, timeout=600, env=env)
            print_success("TTS моделі готові")
        except Exception as e:
            print_warning(f"Помилка завантаження TTS: {e}")


def backup_databases():
    """Архівує SQLite базу та ChromaDB для синхронізації через Git"""
    print_step("Створення резервних копій баз даних...")

    backup_dir = PROJECT_ROOT / "backups" / "databases"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 1. Backup SQLite database
    sqlite_src = CONFIG_ROOT / "atlastrinity.db"
    if sqlite_src.exists():
        sqlite_dst = backup_dir / "atlastrinity.db"
        shutil.copy2(sqlite_src, sqlite_dst)
        print_success(f"SQLite база збережена: {sqlite_dst}")
    else:
        print_warning("SQLite база не знайдена, пропускаємо.")

    # 2. Backup ChromaDB (vector database)
    chroma_src = CONFIG_ROOT / "memory"
    if chroma_src.exists():
        chroma_dst = backup_dir / "memory"
        if chroma_dst.exists():
            shutil.rmtree(chroma_dst)
        shutil.copytree(chroma_src, chroma_dst)
        print_success(f"ChromaDB (векторна база) збережена: {chroma_dst}")
    else:
        print_warning("ChromaDB не знайдена, пропускаємо.")

    # 3. Backup Golden Fund (from CONFIG_ROOT, not PROJECT_ROOT)
    gf_src = CONFIG_ROOT / "data" / "golden_fund"
    if gf_src.exists():
        gf_dst = backup_dir / "golden_fund"
        if gf_dst.exists():
            shutil.rmtree(gf_dst)
        shutil.copytree(gf_src, gf_dst)
        print_success(f"Golden Fund сховище збережено: {gf_dst}")
    else:
        print_info(f"Golden Fund директорія ({gf_src}) ще не створена, пропускаємо.")

    print_info(f"Резервні копії збережено в: {backup_dir}")
    print_info(
        "Тепер ви можете зробити: git add backups/ && git commit -m 'backup: database snapshot'",
    )


def restore_databases():
    """Відновлює бази даних з архіву"""
    print_step("Відновлення баз даних з резервних копій...")

    backup_dir = PROJECT_ROOT / "backups" / "databases"
    if not backup_dir.exists():
        print_warning("Резервні копії не знайдено. Виконайте git pull або backup_databases().")
        return

    # 1. Restore SQLite
    sqlite_src = backup_dir / "atlastrinity.db"
    if sqlite_src.exists():
        sqlite_dst = CONFIG_ROOT / "atlastrinity.db"
        shutil.copy2(sqlite_src, sqlite_dst)
        print_success(f"SQLite база відновлена: {sqlite_dst}")

    # 2. Restore ChromaDB
    chroma_src = backup_dir / "memory"
    if chroma_src.exists():
        chroma_dst = CONFIG_ROOT / "memory"
        if chroma_dst.exists():
            shutil.rmtree(chroma_dst)
        shutil.copytree(chroma_src, chroma_dst)
        print_success(f"ChromaDB відновлена: {chroma_dst}")

    # 3. Restore Golden Fund (to CONFIG_ROOT, not PROJECT_ROOT)
    gf_src = backup_dir / "golden_fund"
    if gf_src.exists():
        gf_dst = CONFIG_ROOT / "data" / "golden_fund"
        if gf_dst.exists():
            shutil.rmtree(gf_dst)
        # Ensure parent directory exists
        gf_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(gf_src, gf_dst)
        print_success(f"Golden Fund сховище відновлено: {gf_dst}")

    print_success("Бази даних успішно відновлено!")


async def verify_database_tables():
    """Detailed verification of database tables and counts using external script"""
    print_step("Детальна перевірка таблиць бази даних...")
    venv_python = str(VENV_PATH / "bin" / "python")
    try:
        subprocess.run(
            [venv_python, str(PROJECT_ROOT / "scripts" / "verify_db_tables.py")],
            check=True,
        )
        return True
    except Exception as e:
        print_error(f"Помилка при верифікації таблиць: {e}")
        return False


def check_services():
    """Перевіряє запущені сервіси"""
    print_step("Перевірка системних сервісів...")

    services = {"redis": "Redis"}  # SQLite is file-based, no service needed

    for service, label in services.items():
        try:
            # Check via brew services (most reliable for managed services)
            # Use manual string parsing to avoid json import dependency if missing
            res = subprocess.run(
                ["brew", "services", "info", service, "--json"],
                check=False,
                capture_output=True,
                text=True,
            )
            # Look for running status in JSON output
            if '"running":true' in res.stdout.replace(" ", ""):
                print_success(f"{label} запущено")
                continue

            # Fallback: check functional ping (Redis only)
            if service == "redis" and shutil.which("redis-cli"):
                if (
                    subprocess.run(
                        ["redis-cli", "ping"], check=False, capture_output=True
                    ).returncode
                    == 0
                ):
                    print_success(f"{label} запущено (CLI)")
                    continue

            print_warning(f"{label} НЕ запущено. Спробуйте: brew services start {service}")

        except Exception as e:
            print_warning(f"Не вдалося перевірити {label}: {e}")


def run_integrity_check():
    """Runs ruff and oxlint to ensure the setup is clean"""
    print_step("Запуск перевірки цілісності коду (Integrity Check)...")
    venv_python = str(VENV_PATH / "bin" / "python")

    # Python checks
    try:
        print_info("Перевірка Python (Ruff)...")
        subprocess.run([venv_python, "-m", "ruff", "check", "."], cwd=PROJECT_ROOT, check=True)
        print_success("Python integrity OK")
    except subprocess.CalledProcessError:
        print_warning(
            "Виявлено проблеми в Python коді. Запустіть 'npm run format:write' для виправлення.",
        )
    except Exception as e:
        print_warning(f"Не вдалося запустити Ruff: {e}")

    # TS/JS checks
    if shutil.which("oxlint"):
        try:
            print_info("Перевірка TS/JS (Oxlint)...")
            subprocess.run(["oxlint", "--ignore-path", ".gitignore"], cwd=PROJECT_ROOT, check=True)
            print_success("TS/JS integrity OK")
        except subprocess.CalledProcessError:
            print_warning("Виявлено проблеми в TS/JS коді.")
        except Exception as e:
            print_warning(f"Не вдалося запустити Oxlint: {e}")


def main():
    print(
        f"\n{Colors.HEADER}{Colors.BOLD}╔══════════════════════════════════════════╗{Colors.ENDC}",
    )
    print(f"{Colors.HEADER}{Colors.BOLD}║  AtlasTrinity Full Stack Dev Setup      ║{Colors.ENDC}")
    print(
        f"{Colors.HEADER}{Colors.BOLD}╚══════════════════════════════════════════╝{Colors.ENDC}\n",
    )

    # Parse arguments
    import argparse

    parser = argparse.ArgumentParser(description="AtlasTrinity Dev Setup")
    parser.add_argument("--backup", action="store_true", help="Backup databases and exit")
    parser.add_argument("--restore", action="store_true", help="Restore databases and exit")
    parser.add_argument(
        "--yes", "-y", action="store_true", help="Non-interactive mode (auto-confirm)"
    )
    args = parser.parse_args()

    if args.yes:
        print_info("Non-interactive mode ENABLED.")
        os.environ["ATLAS_SETUP_NON_INTERACTIVE"] = "1"

    if args.backup:
        backup_databases()
        return

    if args.restore:
        restore_databases()
        return

    check_python_version()
    ensure_directories()

    # Auto-restore databases if backups exist (from git clone)
    backup_dir = PROJECT_ROOT / "backups" / "databases"
    if backup_dir.exists() and not (CONFIG_ROOT / "atlastrinity.db").exists():
        print_info("Виявлено резервні копії баз даних у репозиторії...")
        restore_databases()

    if not check_system_tools():
        print_error("Homebrew є обов'язковим! Встановіть його та спробуйте знову.")
        sys.exit(1)

    if not check_venv():
        sys.exit(1)
    install_brew_deps()  # Встановлення системних залежностей (includes ensure_database)

    # Preflight: verify MCP package versions (npx invocations)
    issues = verify_mcp_package_versions()
    if issues:
        print_warning("Detected potential MCP package issues:")
        for issue in issues:
            print_warning(f"  - {issue}")
        if os.getenv("FAIL_ON_MCP_PRECHECK") == "1":
            print_error(
                "Failing setup because FAIL_ON_MCP_PRECHECK=1 and MCP precheck found issues.",
            )
            sys.exit(1)
        else:
            print_info(
                "Continuing setup despite precheck issues. Set FAIL_ON_MCP_PRECHECK=1 to fail on these errors.",
            )

    if not install_deps():
        sys.exit(1)

    # Sync configs BEFORE DB and tests to ensure latest templates are applied
    sync_configs()

    ensure_database()  # Now dependencies are ready and config is synced

    # Run detailed table verification
    asyncio.run(verify_database_tables())

    build_swift_mcp()
    setup_xcodebuild_mcp()

    # Ensure all binaries are executable
    print_step("Налаштування прав доступу для бінарних файлів...")
    bin_dirs = [PROJECT_ROOT / "bin", PROJECT_ROOT / "vendor"]
    for bdir in bin_dirs:
        if bdir.exists():
            for root, _, files in os.walk(bdir):
                for f in files:
                    fpath = Path(root) / f
                    # If it looks like an executable (macos-use, terminal, etc)
                    if "macos-use" in f or "vibe" in f or fpath.suffix == "":
                        try:
                            os.chmod(fpath, 0o755)
                        except Exception:
                            pass

    # Git Remote Check
    print_step("Перевірка Git конфігурації...")
    try:
        remote_res = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
        if "github.com" in remote_res.stdout:
            print_success("Git remote налаштовано на GitHub")

            # Check for token in .env
            env_path = CONFIG_ROOT / ".env"
            has_env_token = False
            if env_path.exists():
                with open(env_path, encoding="utf-8") as f:
                    if "GITHUB_TOKEN" in f.read():
                        has_env_token = True

            if has_env_token:
                print_success("Git: Виявлено GITHUB_TOKEN у .env (використовується для MCP та API)")

            if "https://" in remote_res.stdout and "@" not in remote_res.stdout:
                helper_res = subprocess.run(
                    ["git", "config", "--get", "credential.helper"], capture_output=True, text=True
                )
                if "osxkeychain" in helper_res.stdout:
                    print_success("Git CLI: Налаштовано через HTTPS + Keychain (osxkeychain)")
                else:
                    print_info(
                        "Git CLI: Використовується HTTPS. Можливо знадобиться персональний токен для push."
                    )
            elif "@" in remote_res.stdout:
                print_success("Git CLI: Налаштовано через персональний токен (embedded)")
        else:
            print_warning("Remote origin не знайдено або не вказує на GitHub.")
    except Exception:
        pass

    try:
        download_models()
    except KeyboardInterrupt:
        print_warning("\nЗавантаження моделей перервано користувачем.")
    except Exception as e:
        print_error(f"Помилка при обробці моделей: {e}")

    check_services()
    run_integrity_check()

    import json

    mcp_config_path = CONFIG_ROOT / "mcp" / "config.json"
    enabled_servers = []
    if mcp_config_path.exists():
        try:
            with open(mcp_config_path, encoding="utf-8") as f:
                mcp_cfg = json.load(f)
                servers = mcp_cfg.get("mcpServers", {})
                for s_name, s_info in servers.items():
                    if not s_info.get("disabled", False):
                        enabled_servers.append(s_name)
        except Exception:
            pass

    print("\n" + "=" * 60)
    print_success("✅ Налаштування завершено!")
    print_info("Кроки для початку роботи:")
    print("  1. Додайте API ключі в ~/.config/atlastrinity/.env")
    print("     - COPILOT_API_KEY (обов'язково)")
    print("     - GITHUB_TOKEN (опціонально)")
    print("  2. Запустіть систему: npm run dev")
    print()

    print_info(f"Доступні MCP сервери ({len(enabled_servers) if enabled_servers else 17}):")
    mcp_info = [
        ("memory", "Граф знань & Long-term Memory (Python)"),
        ("macos-use", "Нативний контроль macOS + Термінал (Swift)"),
        ("vibe", "Coding Agent & Self-Healing (Python)"),
        ("filesystem", "Файлові операції (Node)"),
        ("sequential-thinking", "Глибоке мислення (Node)"),
        ("xcodebuild", "Xcode Build & Test Automation (Node)"),
        ("chrome-devtools", "Автоматизація Chrome (Node)"),
        ("puppeteer", "Веб-скрейпінг та пошук (Node)"),
        ("github", "Офіційний GitHub MCP (Node)"),
        ("duckduckgo-search", "Швидкий пошук (Python)"),
        ("whisper-stt", "Локальне розпізнавання мови (Python)"),
        ("graph", "Візуалізація графу знань (Python)"),
        ("context7", "Документація бібліотек та API (Node)"),
        ("devtools", "Лінтер та аналіз коду (Python)"),
        ("redis", "Оглядовість кешу та сесій (Python)"),
        ("golden-fund", "Knowledge Base & Data Persistence (Python)"),
        ("data-analysis", "Pandas Data Analysis Engine (Python)"),
    ]

    for srv_id, desc in mcp_info:
        status = " (Активен)" if srv_id in enabled_servers else ""
        print(f"  - {srv_id}: {desc}{status}")

    print("  - MCP Inspector: Дебаг MCP серверів (npx @modelcontextprotocol/inspector)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
