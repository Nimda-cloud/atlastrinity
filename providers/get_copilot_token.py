"""
GitHub Copilot Token Retriever
==============================

Отримує ghu_ токен для GitHub Copilot API через OAuth Device Flow.
Працює з двома IDE:
  1. VS Code  — через GitHub Copilot App (client_id: Iv1.b507a08c87ecfe98)
  2. Windsurf — витягує токен з локальної БД Windsurf (state.vscdb)

Використання:
  python -m providers.get_copilot_token                        # Інтерактивний режим
  python -m providers.get_copilot_token --method vscode        # OAuth device flow
  python -m providers.get_copilot_token --method windsurf      # Витягнути з Windsurf DB
  python -m providers.get_copilot_token --update-env           # Оновити .env файли автоматично
  python -m providers.get_copilot_token --test                 # Тільки перевірити поточний токен

Автор: AtlasTrinity Team
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# ─── Constants ───────────────────────────────────────────────────────────────

# GitHub Copilot VS Code App OAuth client ID (public, not a secret)
COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"

GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"

# Editor headers that Copilot API expects
COPILOT_HEADERS = {
    "Editor-Version": "vscode/1.85.0",
    "Editor-Plugin-Version": "copilot/1.144.0",
    "User-Agent": "GithubCopilot/1.144.0",
}

# Paths — providers/ is inside project root
PROJECT_ROOT = Path(__file__).parent.parent
GLOBAL_ENV = Path.home() / ".config" / "atlastrinity" / ".env"
LOCAL_ENV = PROJECT_ROOT / ".env"

# IDE database paths (macOS)
VSCODE_STATE_DB = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Code"
    / "User"
    / "globalStorage"
    / "state.vscdb"
)
WINDSURF_STATE_DB = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Windsurf"
    / "User"
    / "globalStorage"
    / "state.vscdb"
)

# ─── Colors ──────────────────────────────────────────────────────────────────

class C:
    """ANSI color codes for terminal output."""

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

# ─── HTTP Helpers ────────────────────────────────────────────────────────────

def _post_json(url: str, data: dict) -> dict:
    """POST form-encoded data, return JSON response."""
    encoded = urlencode(data).encode()
    req = Request(url, data=encoded, headers={"Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

def _get_json(url: str, headers: dict) -> dict:
    """GET with headers, return JSON response."""
    req = Request(url, headers={**headers, "Accept": "application/json"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())

# ─── Token Verification ─────────────────────────────────────────────────────

def verify_token(token: str) -> dict | None:
    """Verify a ghu_ token against Copilot API. Returns session data or None."""
    headers = {
        "Authorization": f"token {token}",
        **COPILOT_HEADERS,
    }
    try:
        data = _get_json(COPILOT_TOKEN_URL, headers)
        return data
    except HTTPError as e:
        if e.code == 403:
            try:
                body = json.loads(e.read().decode())
                error_msg = body.get("error_details", {}).get("message", body.get("message", ""))
                error(f"403 Forbidden: {error_msg}")
            except Exception:
                error("403 Forbidden: Token rejected by Copilot API")
        elif e.code == 401:
            error("401 Unauthorized: Token is invalid or expired")
        else:
            error(f"HTTP {e.code}: {e.reason}")
        return None
    except Exception as e:
        error(f"Connection error: {e}")
        return None

def print_token_info(data: dict) -> None:
    """Pretty-print Copilot session token info."""
    sku = data.get("sku", "unknown")
    chat = data.get("chat_enabled", False)
    agent = data.get("agent_mode_auto_approval", False)
    individual = data.get("individual", False)
    api_endpoint = data.get("endpoints", {}).get("api", "unknown")
    expires = data.get("expires_at", 0)

    expires_str = (
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expires)) if expires else "unknown"
    )

    print(f"  {C.DIM}SKU:{C.RESET}        {sku}")
    print(f"  {C.DIM}Chat:{C.RESET}       {'✓' if chat else '✗'}")
    print(f"  {C.DIM}Agent:{C.RESET}      {'✓' if agent else '✗'}")
    print(f"  {C.DIM}Individual:{C.RESET} {'✓' if individual else '✗'}")
    print(f"  {C.DIM}API:{C.RESET}        {api_endpoint}")
    print(f"  {C.DIM}Expires:{C.RESET}    {expires_str}")

# ─── Method 1: OAuth Device Flow (VS Code scheme) ───────────────────────────

def get_token_oauth_device_flow() -> str | None:
    """
    Get ghu_ token via GitHub Copilot App OAuth Device Flow.

    This is the same flow VS Code uses internally:
    1. Request device code from GitHub
    2. User authorizes in browser
    3. Poll for access token

    Returns ghu_ token or None on failure.
    """
    step("Starting GitHub Copilot OAuth Device Flow")
    print(f"  {C.DIM}Client ID: {COPILOT_CLIENT_ID} (GitHub Copilot for VS Code){C.RESET}")

    # Step 1: Request device code
    try:
        device_data = _post_json(
            GITHUB_DEVICE_CODE_URL,
            {
                "client_id": COPILOT_CLIENT_ID,
                "scope": "copilot",
            },
        )
    except Exception as e:
        error(f"Failed to request device code: {e}")
        return None

    device_code = device_data["device_code"]
    user_code = device_data["user_code"]
    verification_uri = device_data["verification_uri"]
    expires_in = device_data["expires_in"]
    interval = device_data.get("interval", 5)

    # Step 2: Show user code and open browser
    print()
    print(f"  {C.BOLD}╔══════════════════════════════════════╗{C.RESET}")
    print(
        f"  {C.BOLD}║  Код авторизації: {C.YELLOW}{user_code}{C.RESET}{C.BOLD}          ║{C.RESET}"
    )
    print(f"  {C.BOLD}╚══════════════════════════════════════╝{C.RESET}")
    print()
    print(f"  1. Відкрий: {C.CYAN}{verification_uri}{C.RESET}")
    print(f"  2. Введи код: {C.YELLOW}{user_code}{C.RESET}")
    print("  3. Авторизуй акаунт з Copilot підпискою")
    print(f"  {C.DIM}(код дійсний {expires_in // 60} хвилин){C.RESET}")
    print()

    # Try to open browser automatically
    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", verification_uri], check=False, capture_output=True)
            info("Браузер відкрито автоматично")
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", verification_uri], check=False, capture_output=True)
    except Exception:
        pass

    # Step 3: Poll for token
    print(f"  {C.DIM}Чекаю авторизації...{C.RESET}", end="", flush=True)

    deadline = time.time() + expires_in
    while time.time() < deadline:
        time.sleep(interval)
        print(".", end="", flush=True)

        try:
            token_data = _post_json(
                GITHUB_ACCESS_TOKEN_URL,
                {
                    "client_id": COPILOT_CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
            )
        except Exception as e:
            error(f"\nPoll error: {e}")
            continue

        if "access_token" in token_data:
            token = token_data["access_token"]
            print()
            info(f"Токен отримано: {token[:10]}...{token[-4:]}")
            return token

        err = token_data.get("error", "")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval = token_data.get("interval", interval + 5)
            continue
        if err == "expired_token":
            print()
            error("Код авторизації протермінувався. Спробуйте ще раз.")
            return None
        if err == "access_denied":
            print()
            error("Авторизацію відхилено користувачем.")
            return None
        print()
        error(f"Невідома помилка: {err} - {token_data.get('error_description', '')}")
        return None

    print()
    error("Таймаут очікування авторизації.")
    return None

# ─── Method 2: Extract from IDE DB ──────────────────────────────────────────

def _search_db_for_ghu_token(db_path: Path, ide_name: str) -> str | None:
    """
    Search an IDE's state.vscdb for ghu_ tokens.

    Searches in:
    1. All plaintext values (including terminal history)
    2. GitHub auth secret keys (reports if encrypted)

    Returns the most recent valid ghu_ token found, or None.
    """
    if not db_path.exists():
        error(f"{ide_name} DB not found: {db_path}")
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Show GitHub/Copilot related keys for diagnostics
        cursor.execute(
            "SELECT key FROM ItemTable WHERE key LIKE '%github%' OR key LIKE '%copilot%'"
        )
        keys = [row[0] for row in cursor.fetchall()]
        if keys:
            print(f"  {C.DIM}Знайдені ключі:{C.RESET}")
            for k in keys:
                print(f"    - {k}")

        # Search ALL values for ghu_ tokens (including terminal history, settings, etc.)
        found_tokens: list[str] = []
        cursor.execute("SELECT key, value FROM ItemTable")
        for key, value in cursor.fetchall():
            if isinstance(value, str) and "ghu_" in value:
                for match in re.finditer(r"ghu_[A-Za-z0-9]{36}", value):
                    token = match.group(0)
                    if token not in found_tokens:
                        found_tokens.append(token)
                        print(f"  {C.DIM}Знайдено ghu_ у: {key[:60]}{C.RESET}")

        # Check for encrypted GitHub auth secrets
        cursor.execute("""SELECT key FROM ItemTable WHERE key LIKE '%secret%github%auth%'""")
        secret_rows = cursor.fetchall()
        if secret_rows and not found_tokens:
            warn(f"{ide_name}: GitHub токен зашифрований через Electron safeStorage.")

        # Show logged-in account if available
        cursor.execute("SELECT value FROM ItemTable WHERE key LIKE '%copilot-github%'")
        account_row = cursor.fetchone()
        if account_row:
            info(f"{ide_name} GitHub акаунт: {C.BOLD}{account_row[0]}{C.RESET}")

        conn.close()

        if not found_tokens:
            return None

        # Verify tokens (newest first — last in list is likely most recent)
        for token in reversed(found_tokens):
            print(f"  {C.DIM}Перевіряю {token[:10]}...{C.RESET}")
            data = verify_token(token)
            if data:
                info(f"Валідний токен: {token[:10]}...{token[-4:]}")
                return token
            warn(f"Токен {token[:10]}... невалідний, пробую наступний...")

        return None

    except Exception as e:
        error(f"Помилка читання {ide_name} DB: {e}")
        return None

def get_token_from_windsurf() -> str | None:
    """Try to extract GitHub ghu_ token from Windsurf's state database."""
    step("Searching for GitHub token in Windsurf")
    return _search_db_for_ghu_token(WINDSURF_STATE_DB, "Windsurf")

def get_token_from_vscode() -> str | None:
    """Try to extract GitHub ghu_ token from VS Code's state database."""
    step("Searching for GitHub token in VS Code")
    return _search_db_for_ghu_token(VSCODE_STATE_DB, "VS Code")

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
        # Key doesn't exist — append it
        if not content.endswith("\n"):
            content += "\n"
        new_content = content + f"{key}={value}\n"

    if new_content == content:
        return False

    env_path.write_text(new_content)
    return True

def update_env_file(env_path: Path, token: str) -> bool:
    """Update COPILOT_API_KEY and VISION_API_KEY in an .env file."""
    if not env_path.exists():
        warn(f"Файл не знайдено: {env_path}")
        return False

    changed = False
    changed |= _set_env_var(env_path, "COPILOT_API_KEY", token)
    changed |= _set_env_var(env_path, "VISION_API_KEY", token)

    if changed:
        info(f"Оновлено: {env_path}")
    else:
        warn(f"Нічого не змінено в {env_path}")
    return changed

def update_all_env(token: str) -> None:
    """Update token in LOCAL .env only.

    Providers read from GLOBAL ~/.config/atlastrinity/.env via config.py load_dotenv.
    Scripts write to LOCAL .env which is the source of truth for the project.
    """
    step("Оновлення локального .env")

    if update_env_file(LOCAL_ENV, token):
        info(f"Оновлено: {LOCAL_ENV}")
    else:
        warn(f"Нічого не змінено в {LOCAL_ENV}")

# ─── Test Current Token ─────────────────────────────────────────────────────

def test_current_token() -> bool:
    """Test the currently configured COPILOT_API_KEY."""
    step("Перевірка поточного COPILOT_API_KEY")

    # Load from local .env first, then global
    token = None
    for env_path in [LOCAL_ENV, GLOBAL_ENV]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("COPILOT_API_KEY="):
                    token = line.split("=", 1)[1].strip()
                    break
        if token:
            break

    if not token:
        token = os.getenv("COPILOT_API_KEY")

    if not token:
        error("COPILOT_API_KEY не знайдено ні в .env, ні в environment")
        return False

    print(f"  {C.DIM}Токен: {token[:10]}...{token[-4:]}{C.RESET}")
    print(
        f"  {C.DIM}Тип: {token[:4]}_ ({'User-to-Server' if token.startswith('ghu_') else 'OAuth App' if token.startswith('gho_') else 'PAT' if token.startswith('ghp_') else 'Unknown'}){C.RESET}"
    )

    data = verify_token(token)
    if data:
        info("Токен працює!")
        print_token_info(data)
        return True
    error("Токен НЕ працює")
    return False

# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GitHub Copilot Token Retriever — отримання ghu_ токена для AtlasTrinity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Приклади:
  %(prog)s                        # Інтерактивний режим
  %(prog)s --method vscode        # OAuth device flow
  %(prog)s --method windsurf      # Витягнути з Windsurf
  %(prog)s --test                 # Перевірити поточний токен
  %(prog)s --method vscode --update-env  # Отримати + оновити .env
        """,
    )
    parser.add_argument(
        "--method",
        choices=["vscode", "windsurf", "auto"],
        default=None,
        help="Метод отримання токена (default: інтерактивний вибір)",
    )
    parser.add_argument(
        "--update-env",
        action="store_true",
        help="Автоматично оновити .env файли після отримання токена",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Тільки перевірити поточний COPILOT_API_KEY",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Тихий режим — вивести тільки токен",
    )

    args = parser.parse_args()

    if not args.quiet:
        print(f"\n{C.BOLD}🔑 GitHub Copilot Token Retriever{C.RESET}")
        print(f"{C.DIM}{'─' * 45}{C.RESET}\n")

    # Test mode
    if args.test:
        success = test_current_token()
        sys.exit(0 if success else 1)

    # Determine method
    method = args.method

    if method is None:
        # Interactive mode
        print(f"  {C.BOLD}Оберіть метод отримання токена:{C.RESET}\n")
        print(
            f"  {C.CYAN}1{C.RESET}) OAuth Device Flow {C.DIM}(VS Code scheme — найнадійніший){C.RESET}"
        )
        print(
            f"  {C.CYAN}2{C.RESET}) Витягнути з Windsurf DB {C.DIM}(якщо є збережений токен){C.RESET}"
        )
        print(
            f"  {C.CYAN}3{C.RESET}) Витягнути з VS Code DB {C.DIM}(якщо є збережений токен){C.RESET}"
        )
        print(f"  {C.CYAN}4{C.RESET}) Перевірити поточний токен")
        print()

        try:
            choice = input("  Вибір [1-4]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            sys.exit(0)

        method_map = {"1": "vscode", "2": "windsurf", "3": "vscode_db", "4": "test"}
        method = method_map.get(choice, "vscode")

        if method == "test":
            test_current_token()
            sys.exit(0)

    # Execute method
    token = None

    if method == "auto":
        token = get_token_from_windsurf()
        if not token:
            token = get_token_from_vscode()
        if not token:
            token = get_token_oauth_device_flow()

    elif method == "vscode":
        token = get_token_oauth_device_flow()

    elif method == "vscode_db":
        token = get_token_from_vscode()
        if not token:
            warn("Не вдалося витягнути з DB. Переключаюсь на OAuth Device Flow...")
            token = get_token_oauth_device_flow()

    elif method == "windsurf":
        token = get_token_from_windsurf()
        if not token:
            warn("Не вдалося витягнути з Windsurf. Переключаюсь на OAuth Device Flow...")
            token = get_token_oauth_device_flow()

    if not token:
        error("Не вдалося отримати токен")
        sys.exit(1)

    # Verify token
    step("Верифікація токена")
    data = verify_token(token)
    if data:
        info("Токен валідний!")
        if not args.quiet:
            print_token_info(data)
    else:
        error("Токен отримано, але він не працює з Copilot API")
        error("Переконайтесь що акаунт має активну Copilot підписку")
        sys.exit(1)

    # Output token
    if args.quiet:
        print(token)
    else:
        print(f"\n  {C.BOLD}Токен:{C.RESET} {C.GREEN}{token}{C.RESET}\n")

    # Auto-update .env (always when not in quiet mode, or when --update-env)
    if args.update_env:
        update_all_env(token)
    elif not args.quiet:
        print(f"  {C.DIM}Для автооновлення .env файлів запустіть з --update-env{C.RESET}")

    print()

if __name__ == "__main__":
    main()
