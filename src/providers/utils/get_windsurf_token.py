"""
Windsurf / Codeium Token Extractor
===================================

Витягує API ключ та інформацію про акаунт Windsurf (Codeium) з локальної БД.
Автоматично оновлює .env файли з усіма необхідними параметрами.

Windsurf зберігає auth дані в SQLite базі state.vscdb:
  - API Key (sk-ws-...) — для доступу до Codeium/Windsurf API
  - Installation ID — унікальний ідентифікатор інсталяції
  - API Server URL — endpoint сервера
  - Список доступних моделей з їх конфігурацією
  - Інформація про акаунт (ім'я, тип підписки)

Використання:
  python -m providers.get_windsurf_token                # Показати + оновити .env
  python -m providers.get_windsurf_token --key-only     # Тільки API key
  python -m providers.get_windsurf_token --models       # Показати доступні моделі
  python -m providers.get_windsurf_token --json         # JSON вивід
  python -m providers.get_windsurf_token --test         # Перевірити токен
  python -m providers.get_windsurf_token --no-update    # Не оновлювати .env

Автор: AtlasTrinity Team
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

import requests

# ─── Constants ───────────────────────────────────────────────────────────────

WINDSURF_STATE_DB = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Windsurf"
    / "User"
    / "globalStorage"
    / "state.vscdb"
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
GLOBAL_ENV = Path.home() / ".config" / "atlastrinity" / ".env"
PROJECT_ENV = PROJECT_ROOT / ".env"

# Keys in state.vscdb
KEY_CODEIUM_CONFIG = "codeium.windsurf"
KEY_AUTH_STATUS = "windsurfAuthStatus"
KEY_AUTH_ACCOUNT = "codeium.windsurf-windsurf_auth"

# Default free model for Windsurf
DEFAULT_WINDSURF_MODEL = "deepseek-v3"

# ─── Colors ──────────────────────────────────────────────────────────────────


class C:
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def info(msg: str) -> None:
    pass


def warn(msg: str) -> None:
    pass


def error(msg: str) -> None:
    pass


def step(msg: str) -> None:
    pass


# ─── Data Classes ────────────────────────────────────────────────────────────


@dataclass
class WindsurfModel:
    """A model available in Windsurf."""

    name: str
    model_id: str
    provider: str = ""
    cost_tier: str = ""  # Free, Value, Premium, BYOK


@dataclass
class WindsurfAuth:
    """Windsurf authentication and configuration data."""

    api_key: str = ""
    installation_id: str = ""
    api_server_url: str = ""
    account_name: str = ""
    user_id: str = ""
    models: list[WindsurfModel] = field(default_factory=list)
    raw_auth_status: dict = field(default_factory=dict)
    # Runtime info from running Language Server process
    ls_port: int = 0
    ls_csrf_token: str = ""


# ─── DB Extraction ───────────────────────────────────────────────────────────


def _get_db_value(db_path: Path, key: str) -> str | None:
    """Get a single value from state.vscdb by key."""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as e:
        error(f"DB read error for key '{key}': {e}")
        return None


def _find_account_name(db_path: Path) -> str:
    """Find the Windsurf account name from DB keys."""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT key FROM ItemTable WHERE key LIKE 'windsurf_auth-%' AND key NOT LIKE '%-usages'"
        )
        rows = cursor.fetchall()
        conn.close()

        for (key,) in rows:
            name = key.replace("windsurf_auth-", "")
            if name:
                return name
    except Exception:
        pass
    return ""


def _detect_language_server() -> tuple[int, str]:
    """Detect running Windsurf language server port and CSRF token from process args.

    Returns:
        (port, csrf_token) — port=0 if not found.
    """
    port = 0
    csrf_token = ""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "language_server_macos_arm" not in line or "grep" in line:
                continue
            # Extract CSRF token
            m = re.search(r"--csrf_token\s+(\S+)", line)
            if m:
                csrf_token = m.group(1)
            # Get PID to find listening ports
            parts = line.split()
            if len(parts) >= 2:
                pid = parts[1]
                try:
                    lsof = subprocess.run(
                        ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN", "-a", "-p", pid],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    for lline in lsof.stdout.splitlines():
                        if "LISTEN" in lline:
                            m2 = re.search(r":(\d+)\s+\(LISTEN\)", lline)
                            if m2:
                                candidate = int(m2.group(1))
                                if port == 0 or candidate < port:
                                    port = candidate
                except Exception:
                    pass
            break
    except Exception:
        pass
    return port, csrf_token


def _decode_models_from_proto(configs_b64: list[str]) -> list[WindsurfModel]:
    """Decode model names from protobuf base64 configs."""
    models = []
    for cfg_b64 in configs_b64:
        try:
            raw = base64.b64decode(cfg_b64)
            text = raw.decode("utf-8", errors="replace")
            readable = re.findall(r"[\x20-\x7e\u0400-\u04ff]{3,}", text)
            if readable:
                name = readable[0].strip()
                model_id = ""
                for s in readable:
                    if s.startswith("MODEL_"):
                        model_id = s
                        break
                models.append(WindsurfModel(name=name, model_id=model_id))
        except Exception:
            continue
    return models


def _decode_user_info(user_b64: str) -> tuple[str, str]:
    """Decode user name and ID from protobuf base64."""
    try:
        raw = base64.b64decode(user_b64)
        text = raw.decode("utf-8", errors="replace")
        readable = re.findall(r"[\x20-\x7e\u0400-\u04ff]{3,}", text)

        name = ""
        user_id = ""
        for s in readable:
            if re.match(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", s):
                user_id = s
            elif not name and not s.startswith("MODEL_"):
                name = s
        return name, user_id
    except Exception:
        return "", ""


def _parse_model_categories(auth_status: dict) -> dict[str, list[str]]:
    """Parse model categories (Provider, Cost) from auth status protobuf."""
    categories: dict[str, list[str]] = {
        "free": [],
        "value": [],
        "premium": [],
        "recommended": [],
    }

    user_b64 = auth_status.get("userStatusProtoBinaryBase64", "")
    if not user_b64:
        return categories

    try:
        raw = base64.b64decode(user_b64)
        text = raw.decode("utf-8", errors="replace")
        readable_strings = re.findall(r"[\x20-\x7e\u0400-\u04ff]{3,}", text)

        current_category = ""
        for s in readable_strings:
            s_lower = s.strip().lower()
            if s_lower == "free":
                current_category = "free"
            elif s_lower == "value":
                current_category = "value"
            elif s_lower == "premium":
                current_category = "premium"
            elif s_lower == "recommended":
                current_category = "recommended"
            elif s_lower in ("provider", "cost", "byok", "speed"):
                current_category = ""
            elif current_category and not s.startswith("MODEL_"):
                categories[current_category].append(s.strip())
    except Exception:
        pass

    return categories


def extract_windsurf_auth() -> WindsurfAuth | None:
    """Extract all Windsurf auth data from state.vscdb."""
    if not WINDSURF_STATE_DB.exists():
        error(f"Windsurf DB not found: {WINDSURF_STATE_DB}")
        error("Переконайтесь що Windsurf встановлено і ви хоча б раз залогінились.")
        return None

    auth = WindsurfAuth()

    # 1. Get codeium config (installation ID, API server)
    config_raw = _get_db_value(WINDSURF_STATE_DB, KEY_CODEIUM_CONFIG)
    if config_raw:
        try:
            config = json.loads(config_raw)
            auth.installation_id = config.get("codeium.installationId", "")
            auth.api_server_url = config.get("apiServerUrl", "")
        except json.JSONDecodeError:
            pass

    # 2. Get auth status (API key, models, user info)
    auth_raw = _get_db_value(WINDSURF_STATE_DB, KEY_AUTH_STATUS)
    if auth_raw:
        try:
            auth_status = json.loads(auth_raw)
            auth.raw_auth_status = auth_status
            auth.api_key = auth_status.get("apiKey", "")

            model_configs = auth_status.get("allowedCommandModelConfigsProtoBinaryBase64", [])
            auth.models = _decode_models_from_proto(model_configs)

            user_b64 = auth_status.get("userStatusProtoBinaryBase64", "")
            if user_b64:
                name, uid = _decode_user_info(user_b64)
                if name:
                    auth.account_name = name
                if uid:
                    auth.user_id = uid

        except json.JSONDecodeError:
            pass

    # 3. Fallback: get account name from DB keys
    if not auth.account_name:
        auth.account_name = _find_account_name(WINDSURF_STATE_DB)

    # 4. Detect running Language Server
    ls_port, ls_csrf = _detect_language_server()
    auth.ls_port = ls_port
    auth.ls_csrf_token = ls_csrf

    if not auth.api_key:
        error("API key не знайдено в Windsurf DB")
        return None

    return auth


# ─── .env Update ─────────────────────────────────────────────────────────────


def _set_env_var(env_path: Path, key: str, value: str) -> bool:
    """Set or replace a single key=value in an .env file. Returns True if changed."""
    if not env_path.exists():
        return False

    content = env_path.read_text()
    pattern = rf"^{re.escape(key)}=.*$"

    if re.search(pattern, content, re.MULTILINE):
        new_content = re.sub(pattern, f"{key}={value}", content, flags=re.MULTILINE)
    else:
        # Key doesn't exist — append after a Windsurf comment block or at end
        if "# Windsurf" not in content:
            if not content.endswith("\n"):
                content += "\n"
            content += "# Windsurf/Codeium\n"
        if not content.endswith("\n"):
            content += "\n"
        new_content = content + f"{key}={value}\n"

    if new_content == content:
        return False

    env_path.write_text(new_content)
    return True


def update_env_windsurf(auth: WindsurfAuth) -> None:
    """Update all Windsurf-related variables in PROJECT .env.

    The .env file in project root is the source of truth for all environment variables.
    System reads from this file and syncs to global location.
    """
    step("Оновлення .env файлу проекту (Windsurf)")

    if not PROJECT_ENV.exists():
        warn(f"Файл не знайдено: {PROJECT_ENV}")
        return

    vars_to_set = {
        "WINDSURF_API_KEY": auth.api_key,
        "WINDSURF_INSTALL_ID": auth.installation_id,
        "WINDSURF_MODEL": DEFAULT_WINDSURF_MODEL,
    }
    if auth.ls_port:
        vars_to_set["WINDSURF_LS_PORT"] = str(auth.ls_port)
    if auth.ls_csrf_token:
        vars_to_set["WINDSURF_LS_CSRF"] = auth.ls_csrf_token

    changed = False
    for key, value in vars_to_set.items():
        if value:
            changed |= _set_env_var(PROJECT_ENV, key, value)

    if changed:
        info(f"Оновлено: {PROJECT_ENV}")
        # Sync to global location using existing setup script
        try:
            import subprocess
            import sys

            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "scripts" / "setup_dev.py")],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
            )

            if result.returncode == 0:
                pass
            else:
                pass
        except Exception:
            pass
    else:
        pass


# ─── Token Test ──────────────────────────────────────────────────────────────


def test_windsurf_token(api_key: str, api_server_url: str = "") -> bool:
    """Test Windsurf API key by making a health check request."""
    server = api_server_url or "https://server.self-serve.windsurf.com"

    try:
        resp = requests.post(
            f"{server}/exa.api_server_pb.ApiServerService/GetUser",
            data="{}",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {api_key}",
            },
            timeout=10,
        )
        info(f"API server responded: HTTP {resp.status_code}")
        return True
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else None
        if status_code == 401:
            error("401 Unauthorized — API key невалідний або протермінований")
            return False
        if status_code == 404:
            info(f"API server reachable (HTTP {status_code})")
            return True
        if status_code in (200, 400):
            info(f"API server responded: HTTP {status_code}")
            return True
        warn(f"API server responded with HTTP {status_code}")
        return True
    except requests.exceptions.RequestException as e:
        error(f"Cannot reach API server {server}: {e}")
        return False


# ─── Display ─────────────────────────────────────────────────────────────────


def print_auth_info(auth: WindsurfAuth) -> None:
    """Pretty-print Windsurf auth information."""
    if auth.user_id:
        pass
    if auth.ls_port:
        pass
    if auth.ls_csrf_token:
        pass


def print_models(auth: WindsurfAuth) -> None:
    """Print available models grouped by category."""
    categories = _parse_model_categories(auth.raw_auth_status)

    if auth.models:
        step(f"Доступні моделі ({len(auth.models)} default)")
        for i, m in enumerate(auth.models):
            pass

    for tier, tier_models in categories.items():
        if tier_models:
            {
                "free": C.GREEN,
                "value": C.YELLOW,
                "premium": C.RED,
                "recommended": C.CYAN,
            }.get(tier, C.DIM)
            for m in tier_models:
                pass


def output_json(auth: WindsurfAuth) -> None:
    """Output auth data as JSON."""
    {
        "api_key": auth.api_key,
        "installation_id": auth.installation_id,
        "api_server_url": auth.api_server_url,
        "account_name": auth.account_name,
        "user_id": auth.user_id,
        "models": [{"name": m.name, "model_id": m.model_id} for m in auth.models],
        "ls_port": auth.ls_port,
        "ls_csrf_token": auth.ls_csrf_token,
    }


# ─── Main ────────────────────────────────────────────────────────────────────


def main() -> None:
    """Main entry point for Windsurf token extraction."""
    parser = argparse.ArgumentParser(
        description="Windsurf / Codeium Token Extractor — витягує API ключ з локальної БД Windsurf",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Приклади:
  %(prog)s                  # Показати інфо + оновити .env
  %(prog)s --key-only       # Тільки API key (для скриптів)
  %(prog)s --models         # Показати доступні моделі
  %(prog)s --json           # JSON вивід
  %(prog)s --test           # Перевірити з'єднання з API
  %(prog)s --no-update      # Не оновлювати .env файли
        """,
    )
    parser.add_argument(
        "--key-only",
        action="store_true",
        help="Вивести тільки API key (для використання в скриптах)",
    )
    parser.add_argument(
        "--models",
        action="store_true",
        help="Показати доступні моделі",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Вивести у форматі JSON",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Перевірити з'єднання з Windsurf API",
    )
    parser.add_argument(
        "--no-update",
        action="store_true",
        help="Не оновлювати .env файли автоматично",
    )

    args = parser.parse_args()

    # Extract auth
    auth = extract_windsurf_auth()
    if not auth:
        sys.exit(1)

    # Key-only mode
    if args.key_only:
        sys.exit(0)

    # JSON mode
    if args.json:
        output_json(auth)
        sys.exit(0)

    # Normal output

    step("Windsurf Auth Info")
    print_auth_info(auth)

    # Test mode
    if args.test:
        step("Перевірка з'єднання з API")
        test_windsurf_token(auth.api_key, auth.api_server_url)

    # Models
    if args.models:
        print_models(auth)

    # Full API key display

    # Auto-update .env (default behavior)
    if not args.no_update:
        update_env_windsurf(auth)
    else:
        pass


# Export main function for module imports
__all__ = ["main"]

if __name__ == "__main__":
    main()
