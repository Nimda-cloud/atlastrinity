#!/usr/bin/env python3
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
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

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

PROJECT_ROOT = Path(__file__).parent.parent
GLOBAL_ENV = Path.home() / ".config" / "atlastrinity" / ".env"
LOCAL_ENV = PROJECT_ROOT / ".env"

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
    print(f"{C.GREEN}✓{C.RESET} {msg}")


def warn(msg: str) -> None:
    print(f"{C.YELLOW}⚠{C.RESET} {msg}")


def error(msg: str) -> None:
    print(f"{C.RED}✗{C.RESET} {msg}")


def step(msg: str) -> None:
    print(f"\n{C.CYAN}▸{C.RESET} {C.BOLD}{msg}{C.RESET}")


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
    """Update all Windsurf-related variables in LOCAL .env only.

    Providers read from GLOBAL ~/.config/atlastrinity/.env via config.py load_dotenv.
    Scripts write to LOCAL .env which is the source of truth for the project.
    """
    step("Оновлення локального .env (Windsurf)")

    if not LOCAL_ENV.exists():
        warn(f"Файл не знайдено: {LOCAL_ENV}")
        return

    vars_to_set = {
        "WINDSURF_API_KEY": auth.api_key,
        "WINDSURF_INSTALL_ID": auth.installation_id,
        "WINDSURF_MODEL": DEFAULT_WINDSURF_MODEL,
    }

    changed = False
    for key, value in vars_to_set.items():
        if value:
            changed |= _set_env_var(LOCAL_ENV, key, value)

    if changed:
        info(f"Оновлено: {LOCAL_ENV}")
    else:
        print(f"  {C.DIM}Без змін: {LOCAL_ENV}{C.RESET}")


# ─── Token Test ──────────────────────────────────────────────────────────────


def test_windsurf_token(api_key: str, api_server_url: str = "") -> bool:
    """Test Windsurf API key by making a health check request."""
    server = api_server_url or "https://server.self-serve.windsurf.com"

    try:
        req = Request(
            f"{server}/exa.api_server_pb.ApiServerService/GetUser",
            data=b"{}",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {api_key}",
            },
        )
        with urlopen(req, timeout=10) as resp:
            info(f"API server responded: HTTP {resp.getcode()}")
            return True
    except HTTPError as e:
        if e.code == 401:
            error("401 Unauthorized — API key невалідний або протермінований")
            return False
        if e.code == 404:
            info(f"API server reachable (HTTP {e.code})")
            return True
        if e.code in (200, 400):
            info(f"API server responded: HTTP {e.code}")
            return True
        warn(f"API server responded with HTTP {e.code}")
        return True
    except Exception as e:
        error(f"Cannot reach API server {server}: {e}")
        return False


# ─── Display ─────────────────────────────────────────────────────────────────


def print_auth_info(auth: WindsurfAuth) -> None:
    """Pretty-print Windsurf auth information."""
    print(f"  {C.DIM}Account:{C.RESET}        {C.BOLD}{auth.account_name}{C.RESET}")
    if auth.user_id:
        print(f"  {C.DIM}User ID:{C.RESET}        {auth.user_id}")
    print(f"  {C.DIM}API Key:{C.RESET}        {auth.api_key[:15]}...{auth.api_key[-8:]}")
    print(f"  {C.DIM}API Key len:{C.RESET}    {len(auth.api_key)}")
    print(f"  {C.DIM}Installation:{C.RESET}   {auth.installation_id}")
    print(f"  {C.DIM}API Server:{C.RESET}     {auth.api_server_url}")


def print_models(auth: WindsurfAuth) -> None:
    """Print available models grouped by category."""
    categories = _parse_model_categories(auth.raw_auth_status)

    if auth.models:
        step(f"Доступні моделі ({len(auth.models)} default)")
        for i, m in enumerate(auth.models):
            print(f"  {C.CYAN}{i + 1:2d}{C.RESET}. {m.name} {C.DIM}({m.model_id}){C.RESET}")

    for tier, tier_models in categories.items():
        if tier_models:
            tier_color = {
                "free": C.GREEN,
                "value": C.YELLOW,
                "premium": C.RED,
                "recommended": C.CYAN,
            }.get(tier, C.DIM)
            print(f"\n  {tier_color}{C.BOLD}{tier.upper()}{C.RESET} ({len(tier_models)}):")
            for m in tier_models:
                print(f"    - {m}")


def output_json(auth: WindsurfAuth) -> None:
    """Output auth data as JSON."""
    data = {
        "api_key": auth.api_key,
        "installation_id": auth.installation_id,
        "api_server_url": auth.api_server_url,
        "account_name": auth.account_name,
        "user_id": auth.user_id,
        "models": [{"name": m.name, "model_id": m.model_id} for m in auth.models],
    }
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
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
        print(auth.api_key)
        sys.exit(0)

    # JSON mode
    if args.json:
        output_json(auth)
        sys.exit(0)

    # Normal output
    print(f"\n{C.BOLD}🌊 Windsurf / Codeium Token Extractor{C.RESET}")
    print(f"{C.DIM}{'─' * 45}{C.RESET}")

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
    print(f"\n  {C.BOLD}API Key (повний):{C.RESET}")
    print(f"  {C.GREEN}{auth.api_key}{C.RESET}")

    # Auto-update .env (default behavior)
    if not args.no_update:
        update_env_windsurf(auth)
    else:
        print(f"\n  {C.DIM}Оновлення .env пропущено (--no-update){C.RESET}")

    print()


if __name__ == "__main__":
    main()
