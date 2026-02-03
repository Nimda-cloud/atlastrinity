#!/usr/bin/env python3
"""
Quick Google Maps API Key Setup Helper
Запускайте цей скрипт, щоб автоматично отримати і налаштувати справжній API ключ.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


def print_header(msg):
    print(f"\n\033[1;96m=== {msg} ===\033[0m\n")


def print_success(msg):
    print(f"\033[92m✓\033[0m {msg}")


def print_error(msg):
    print(f"\033[91m✗\033[0m {msg}")


def print_info(msg):
    print(f"\033[94mℹ\033[0m {msg}")


def check_current_key():
    """Перевірка наявності ключа в .env"""
    if not ENV_FILE.exists():
        print_error(f".env файл не знайдено: {ENV_FILE}")
        return None

    with open(ENV_FILE, encoding="utf-8") as f:
        content = f.read()

    # Шукаємо ключ
    match = re.search(r"GOOGLE_MAPS_API_KEY=(AIza[a-zA-Z0-9_\-]+)", content)
    if not match:
        return None

    key = match.group(1)
    # Перевірка чи це placeholder
    if "AIzaSyBq4tcSGVtpl" in key:
        print_info(f"Знайдено PLACEHOLDER ключ: {key[:20]}...")
        return None

    print_success(f"Знайдено діючий ключ: {key[:10]}...")
    return key


def offer_manual_setup():
    """Пропонує налаштувати через веб-консоль"""
    print_header("Налаштування Google Maps API")
    print("Для роботи Street View потрібен РЕАЛЬНИЙ API ключ з Google Cloud.\n")

    print("📋 ПОКРОКОВА ІНСТРУКЦІЯ:\n")
    print("1️⃣  Відкрийте Google Cloud Console:")
    print("   \033[94mhttps://console.cloud.google.com/\033[0m\n")

  print("2️⃣  Створіть або виберіть проект (наприклад, 'atlastrinity')\n")

    print("3️⃣  Увімкніть необхідні API:")
    print("   \033[94mhttps://console.cloud.google.com/apis/library\033[0m")
    print("   - Maps JavaScript API")
    print("   - Places API")
    print("   - Geocoding API")
    print("   - Street View Static API\n")

    print("4️⃣  Створіть API ключ:")
    print("   \033[94mhttps://console.cloud.google.com/apis/credentials\033[0m")
    print("   Натисніть: CREATE CREDENTIALS → API Key\n")

    print("5️⃣  ⚠️  ВАЖЛИВО: Підключіть Billing Account!")
    print("   Без білінгу Street View не працюватиме.\n")

    print("6️⃣  (Опціонально) Налаштуйте обмеження ключа:")
    print("   - Application restrictions: HTTP referrers")
    print("   - API restrictions: обрані вище API\n")

    print("-" * 60)
    api_key = input("\n📝 Введіть ваш API ключ (AIza...): ").strip()

    if not api_key.startswith("AIza"):
        print_error("Невірний формат ключа! Ключі Google починаються з 'AIza'")
        sys.exit(1)

    return api_key


def update_env_file(api_key):
    """Оновлює .env файл новим ключем"""
    print_info("Оновлення .env файлу...")

    if not ENV_FILE.exists():
        ENV_FILE.touch()

    with open(ENV_FILE, encoding="utf-8") as f:
        content = f.read()

    # Оновлення GOOGLE_MAPS_API_KEY
    key_pattern = r"^GOOGLE_MAPS_API_KEY=.*$"
    new_line = f"GOOGLE_MAPS_API_KEY={api_key}"
    if re.search(key_pattern, content, re.M):
        content = re.sub(key_pattern, new_line, content, flags=re.M)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += new_line + "\n"

    # Оновлення VITE_GOOGLE_MAPS_API_KEY
    vite_pattern = r"^VITE_GOOGLE_MAPS_API_KEY=.*$"
    vite_line = f"VITE_GOOGLE_MAPS_API_KEY={api_key}"
    if re.search(vite_pattern, content, re.M):
        content = re.sub(vite_pattern, vite_line, content, flags=re.M)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += vite_line + "\n"

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print_success(".env файл оновлено!")
    print_info(f"Ключ збережено в: {ENV_FILE}")


def sync_to_global_config():
    """Синхронізує .env до глобального конфігу"""
    global_env = Path.home() / ".config" / "atlastrinity" / ".env"
    if global_env.exists():
        try:
            import shutil

            shutil.copy2(ENV_FILE, global_env)
            print_success(f"Синхронізовано з глобальним конфігом: {global_env}")
        except Exception as e:
            print_error(f"Не вдалося синхронізувати: {e}")


def main():
    print_header("Atlas Trinity - Quick Google Maps Setup")

    current_key = check_current_key()
    if current_key:
        print("\nУ вас вже є діючий API ключ.")
        choice = input("Замінити його? (y/n): ").lower()
        if choice != "y":
            print_info("Скасовано.")
            return

    # Check if gcloud is available for automated setup
    if subprocess.run(["which", "gcloud"], capture_output=True).returncode == 0:
        print_info("Знайдено gcloud CLI. Запустіть для автоматичного налаштування:")
        print(f"  \033[1mpython3 {PROJECT_ROOT / 'scripts' / 'setup_google_maps.py'}\033[0m\n")

        choice = input("Використати gcloud для автоматичного налаштування? (y/n): ").lower()
        if choice == "y":
            subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "setup_google_maps.py")])
            return

    api_key = offer_manual_setup()
    update_env_file(api_key)
    sync_to_global_config()

    print("\n" + "=" * 60)
    print_success("Налаштування завершено!")
    print_info("Перезапустіть додаток: npm run dev")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
