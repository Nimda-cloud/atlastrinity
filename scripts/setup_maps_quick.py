#!/usr/bin/env python3
"""
Unified Google Maps API Setup Script
Об'єднує автоматичне (gcloud) та ручне налаштування Google Maps API
"""
import json
import os
import random
import re
import shutil
import string
import subprocess
import sys
import time
from pathlib import Path

# --- Constants ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
REQUIRED_SERVICES = [
    "maps-backend.googleapis.com",
    "static-maps-backend.googleapis.com",
    "street-view-image-backend.googleapis.com",
    "directions-backend.googleapis.com",
    "places-backend.googleapis.com",
    "geocoding-backend.googleapis.com",
    "addressvalidation.googleapis.com",
]


class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_step(msg):
    print(f"{Colors.BOLD}{Colors.OKBLUE}[GCP]{Colors.ENDC} {msg}")


def print_success(msg):
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {msg}")


def print_warning(msg):
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {msg}")


def print_error(msg):
    print(f"{Colors.FAIL}✗{Colors.ENDC} {msg}")


def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {msg}")


def run_command(cmd, capture_output=True, check=True):
    try:
        result = subprocess.run(
            cmd, capture_output=capture_output, text=True, check=check, shell=isinstance(cmd, str)
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise e
        return e


def check_current_key():
    """Перевірка наявності ключа в .env"""
    if not ENV_FILE.exists():
        return None

    with open(ENV_FILE, encoding="utf-8") as f:
        content = f.read()

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


def check_gcloud():
    """Перевірка та встановлення gcloud CLI якщо потрібно"""
    print_step("Перевірка gcloud installation...")
    if subprocess.run(["which", "gcloud"], capture_output=True).returncode != 0:
        print_warning("gcloud CLI не знайдено.")
        
        # Check if Homebrew is available for installation
        if shutil.which("brew"):
            print_info("Знайдено Homebrew. Пропоную встановити Google Cloud SDK...")
            choice = input("Встановити gcloud CLI через Homebrew? (y/n): ").lower()
            
            if choice == "y":
                try:
                    print_info("Встановлення google-cloud-sdk...")
                    subprocess.run(
                        ["brew", "install", "--cask", "google-cloud-sdk"], 
                        check=True
                    )
                    print_success("Google Cloud SDK встановлено успішно!")
                    
                    # Add to PATH for current session
                    gcloud_paths = [
                        "/opt/homebrew/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin",
                        "/usr/local/Caskroom/google-cloud-sdk/latest/google-cloud-sdk/bin"
                    ]
                    for gcloud_path in gcloud_paths:
                        if Path(gcloud_path).exists():
                            os.environ["PATH"] = gcloud_path + ":" + os.environ.get("PATH", "")
                            print_info(f"Додано до PATH: {gcloud_path}")
                            break
                    
                    # Verify installation
                    if subprocess.run(["which", "gcloud"], capture_output=True).returncode == 0:
                        print_success("gcloud тепер доступний!")
                        return True
                    else:
                        print_warning("gcloud встановлено, але потребує перезапуску термінала")
                        print_info("Після перезапуску запустіть: python3 scripts/setup_maps_quick.py")
                        return False
                        
                except subprocess.CalledProcessError as e:
                    print_error(f"Не вдалося встановити gcloud: {e}")
                    return False
            else:
                print_info("Встановлення gcloud пропущено.")
                return False
        else:
            print_warning("Homebrew не знайдено. Не можу автоматично встановити gcloud.")
            print_info("Встановіть вручну: https://cloud.google.com/sdk/docs/install")
            return False
            
    print_success("gcloud знайдено")
    return True


def check_auth():
    print_step("Перевірка Google Cloud authentication...")
    result = run_command(["gcloud", "auth", "list", "--format=json"], check=False)
    if result.returncode != 0:
        print_info("Не автентифіковано. Запуск браузера для логіну...")
        run_command(["gcloud", "auth", "login"], capture_output=False)
    else:
        try:
            auths = json.loads(result.stdout)
            active_auth = next((a for a in auths if a.get("active", False)), None)
            if active_auth:
                print_success(f"Автентифіковано як: {active_auth['account']}")
            else:
                print_info("Активний аккаунт не знайдено. Запуск логіну...")
                run_command(["gcloud", "auth", "login"], capture_output=False)
        except Exception:
            run_command(["gcloud", "auth", "login"], capture_output=False)


def get_or_create_project():
    print_step("Управління GCP проектом...")

    # Check current project
    result = run_command(["gcloud", "config", "get-value", "project"], check=False)
    current_project = result.stdout.strip()

    if current_project and "(unset)" not in current_project:
        print_info(f"Поточний проект: {Colors.BOLD}{current_project}{Colors.ENDC}")
        choice = input("Використати цей проект? (y/n/create): ").lower()
        if choice == "y":
            return current_project
        elif choice == "create":
            return create_project()

    # List projects
    print_info("Отримання списку проектів...")
    result = run_command(["gcloud", "projects", "list", "--format=json"])
    projects = json.loads(result.stdout)

    if not projects:
        print_warning("Проектів не знайдено.")
        return create_project()

    print("\nДоступні проекти:")
    for i, p in enumerate(projects):
        print(f"{i + 1}) {p['projectId']} ({p['name']})")
    print(f"{len(projects) + 1}) [Створити новий проект]")

    try:
        idx = int(input(f"\nВиберіть проект (1-{len(projects) + 1}): ")) - 1
        if idx == len(projects):
            return create_project()
        project_id = projects[idx]["projectId"]
        run_command(["gcloud", "config", "set", "project", project_id])
        return project_id
    except (ValueError, IndexError):
        print_error("Невірний вибір")
        sys.exit(1)


def create_project():
    """Створення нового GCP проекту з обробкою помилок"""
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    project_id = f"atlastrinity-maps-{suffix}"
    print_step(f"Створення нового проекту: {project_id}...")
    
    try:
        # Try to create project (may fail if user doesn't have org permissions)
        result = run_command(
            ["gcloud", "projects", "create", project_id, "--name=AtlasTrinityMaps"],
            check=False
        )
        
        if result.returncode != 0:
            stderr = result.stderr if result.stderr else "Невідома помилка"
            
            # Check for Terms of Service error specifically
            if "Terms of Service" in stderr or "TOS" in stderr:
                print_error("Помилка: Необхідно прийняти Умови використання Google Cloud.")
                print_warning("\n⚠️  КРИТИЧНА ДІЯ:")
                print("CLI не може прийняти Умови використання за вас з юридичних причин.")
                print(f"\n1. Відкрийте це посилання: {Colors.BOLD}{Colors.OKCYAN}https://console.cloud.google.com/terms{Colors.ENDC}")
                print("2. Виберіть вашу країну та натисніть 'Agree and Continue'")
                print("3. Поверніться сюди та натисніть Enter\n")
                input("Натисніть Enter ПІСЛЯ того як приймете умови в браузері...")
                
                # Retry project creation after TOS acceptance
                return create_project()

            print_error("Не вдалося створити проект автоматично.")
            print_warning("Деталі помилки:")
            print(stderr)
            
            print_info("\n📌 Можливі причини:")
            print("  • Потрібна організація Google Cloud (Organization)")
            print("  • Недостатньо прав для створення проектів")
            print("  • Досягнуто ліміт проектів для акаунту")
            
            print_info("\n💡 Рішення:")
            print("  1) Створіть проект вручну: https://console.cloud.google.com/projectcreate")
            print("  2) Або зверніться до адміністратора організації для надання прав\n")
            
            choice = input("Ви вже створили проект вручну? (y/n): ").lower()
            if choice == "y":
                manual_project_id = input("Введіть Project ID (наприклад, 'my-project-123'): ").strip()
                if manual_project_id:
                    # Verify project exists
                    verify = run_command(
                        ["gcloud", "projects", "describe", manual_project_id, "--format=json"],
                        check=False
                    )
                    if verify.returncode == 0:
                        run_command(["gcloud", "config", "set", "project", manual_project_id])
                        print_success(f"Проект {manual_project_id} встановлено як активний")
                        return manual_project_id
                    else:
                        print_error(f"Проект '{manual_project_id}' не знайдено.")
                        print_info("Перевірте Project ID в консолі: https://console.cloud.google.com")
                        sys.exit(1)
            else:
                print_info("Створіть проект і запустіть скрипт знову.")
                sys.exit(1)
        else:
            # Project created successfully
            run_command(["gcloud", "config", "set", "project", project_id])
            print_success(f"Проект {project_id} створено і встановлено як активний")
            
            print_warning(
                "ВАЖЛИВО: Необхідно увімкнути Billing для цього проекту в Google Cloud Console."
            )
            print_warning(
                "Без білінгу карти матимуть watermark 'for development purposes only' і будуть темними."
            )
            print(f"URL: https://console.cloud.google.com/billing/linkedaccount?project={project_id}")
            input("\nНатисніть Enter після підключення Billing account...")
            
            return project_id
            
    except Exception as e:
        print_error(f"Несподівана помилка: {e}")
        print_info("Будь ласка, створіть проект вручну: https://console.cloud.google.com/projectcreate")
        sys.exit(1)


def check_billing(project_id):
    """Перевірка прив'язки Білінгу до проекту"""
    print_step("Перевірка статусу Billing...")
    try:
        result = run_command(
            ["gcloud", "billing", "projects", "describe", project_id, "--format=json"], check=False
        )
        if result.returncode == 0:
            billing_info = json.loads(result.stdout)
            if billing_info.get("billingEnabled"):
                print_success(f"Billing УВІМКНЕНИЙ для проекту {project_id}")
                return True

        print_warning(f"Billing НЕ увімкнений для проекту {project_id}")
        print_info("Без білінгу карти матимуть watermark 'for development purposes only'.")
        print(f"URL: https://console.cloud.google.com/billing/linkedaccount?project={project_id}")
        choice = input("\nПродовжити без білінгу? (y/n): ").lower()
        return choice == "y"
    except Exception as e:
        print_warning(f"Не вдалося перевірити статус білінгу: {e}")
        return True


def enable_apis(project_id):
    print_step("Перевірка та увімкнення необхідних Google Maps API...")

    # Get currently enabled services
    enabled_result = run_command(
        ["gcloud", "services", "list", "--enabled", "--project", project_id, "--format=json"]
    )
    enabled_names = [s["config"]["name"] for s in json.loads(enabled_result.stdout)]

    for service in REQUIRED_SERVICES:
        if service in enabled_names:
            print_success(f"Сервіс {service} вже увімкнений")
        else:
            try:
                print(f"  Увімкнення {service}...")
                run_command(["gcloud", "services", "enable", service, "--project", project_id])
                print_success(f"Сервіс {service} увімкнено")
            except Exception as e:
                print_warning(f"Не вдалося увімкнути {service}. Можливо, потрібен Білінг.")
                print_info(f"Продовжуємо налаштування інших API...")
    print_success("Процес увімкнення API завершено")


def ensure_key_unrestricted(project_id, key_name):
    """Знімає обмеження з ключа для уникнення ApiTargetBlockedMapError"""
    print_step("Оптимізація обмежень API ключа...")
    try:
        print_info(f"Очищення обмежень для ключа: {key_name}")
        run_command(
            [
                "gcloud",
                "alpha",
                "services",
                "api-keys",
                "update",
                key_name,
                "--clear-restrictions",
                "--project",
                project_id,
            ]
        )
        print_success("Обмеження API ключа очищено (Повний доступ увімкнено)")
    except Exception as e:
        print_warning(f"Не вдалося очистити обмеження автоматично: {e}")


def get_or_create_api_key(project_id):
    print_step("Управління API ключем...")

    print_info("Перевірка наявних API ключів...")

    try:
        result = run_command(
            [
                "gcloud",
                "alpha",
                "services",
                "api-keys",
                "list",
                "--project",
                project_id,
                "--format=json",
            ],
            check=False,
        )
        if result.returncode == 0:
            keys = json.loads(result.stdout)
            trinity_key = next(
                (k for k in keys if k.get("displayName") == "AtlasTrinity Key"), None
            )
            if trinity_key:
                key_name = trinity_key["name"]
                print_info("Знайдено існуючий AtlasTrinity Key, отримання значення...")
                desc = run_command(
                    ["gcloud", "alpha", "services", "api-keys", "get-key-string", key_name],
                    check=False,
                )
                if desc.returncode == 0:
                    api_key = desc.stdout.strip().split("keyString: ")[-1]
                    ensure_key_unrestricted(project_id, key_name)
                    return api_key

        print_info("Створення нового API ключа...")
        name_result = run_command(
            [
                "gcloud",
                "alpha",
                "services",
                "api-keys",
                "create",
                "--display-name=AtlasTrinity Key",
                "--project",
                project_id,
                "--format=json",
            ]
        )
        key_info = json.loads(name_result.stdout)
        key_res_name = key_info["name"]
        print_info("Очікування поширення ключа...")
        time.sleep(5)
        desc = run_command(
            ["gcloud", "alpha", "services", "api-keys", "get-key-string", key_res_name]
        )
        api_key = desc.stdout.strip().split("keyString: ")[-1].strip()
        ensure_key_unrestricted(project_id, key_res_name)
        return api_key

    except Exception as e:
        print_warning(f"Не вдалося автоматизувати створення API ключа через CLI: {e}")
        print_info(
            "Будь ласка, створіть API ключ вручну: https://console.cloud.google.com/google/maps-apis/credentials"
        )
        api_key = input("Введіть ваш API ключ: ").strip()
        return api_key


def offer_manual_setup():
    """Ручне налаштування через веб-консоль"""
    print_step("Ручне налаштування Google Maps API")
    print("Для роботи Street View потрібен РЕАЛЬНИЙ API ключ з Google Cloud.\n")

    print("📋 ПОКРОКОВА ІНСТРУКЦІЯ:\n")
    print("1️⃣  Відкрийте Google Cloud Console:")
    print(f"   {Colors.OKCYAN}https://console.cloud.google.com/{Colors.ENDC}\n")

    print("2️⃣  Створіть або виберіть проект (наприклад, 'atlastrinity')\n")

    print("3️⃣  Увімкніть необхідні API:")
    print(f"   {Colors.OKCYAN}https://console.cloud.google.com/apis/library{Colors.ENDC}")
    print("   - Maps JavaScript API")
    print("   - Places API")
    print("   - Geocoding API")
    print("   - Street View Static API\n")

    print("4️⃣  Створіть API ключ:")
    print(f"   {Colors.OKCYAN}https://console.cloud.google.com/apis/credentials{Colors.ENDC}")
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


def update_env(api_key):
    print_step("Оновлення .env файлу...")
    if not ENV_FILE.exists():
        example = PROJECT_ROOT / ".env.example"
        if example.exists():
            shutil.copy2(example, ENV_FILE)
            print_info("Створено .env з .env.example")
        else:
            ENV_FILE.touch()

    with open(ENV_FILE, encoding="utf-8") as f:
        content = f.read()

    key_pattern = r"^GOOGLE_MAPS_API_KEY=.*$"
    vite_key_pattern = r"^VITE_GOOGLE_MAPS_API_KEY=.*$"

    new_line = f"GOOGLE_MAPS_API_KEY={api_key}"
    vite_new_line = f"VITE_GOOGLE_MAPS_API_KEY={api_key}"

    # Update or Add GOOGLE_MAPS_API_KEY
    if re.search(key_pattern, content, re.M):
        content = re.sub(key_pattern, new_line, content, flags=re.M)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += new_line + "\n"

    # Update or Add VITE_GOOGLE_MAPS_API_KEY
    if re.search(vite_key_pattern, content, re.M):
        content = re.sub(vite_key_pattern, vite_new_line, content, flags=re.M)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += vite_new_line + "\n"

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print_success(".env файл оновлено з GOOGLE_MAPS_API_KEY")

    # Sync to global config
    global_env = Path.home() / ".config" / "atlastrinity" / ".env"
    global_env.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(ENV_FILE, global_env)
        print_success(f"Синхронізовано з глобальним конфігом: {global_env}")
    except Exception as e:
        print_warning(f"Не вдалося синхронізувати: {e}")


def main():
    print(f"\n{Colors.BOLD}{Colors.HEADER}=== AtlasTrinity Google Maps Setup ==={Colors.ENDC}\n")

    # Check existing key
    current_key = check_current_key()
    if current_key:
        print("\nУ вас вже є діючий API ключ.")
        choice = input("Замінити його? (y/n): ").lower()
        if choice != "y":
            print_info("Скасовано.")
            return

    # Check if gcloud is available
    has_gcloud = check_gcloud()

    if has_gcloud:
        print_info("\n📌 Доступні режими налаштування:")
        print("  1) Автоматичне (через gcloud CLI)")
        print("  2) Ручне (через веб-консоль)\n")
        choice = input("Виберіть режим (1/2): ").strip()

        if choice == "1":
            # Automated gcloud setup
            check_auth()
            project_id = get_or_create_project()
            check_billing(project_id)
            enable_apis(project_id)
            api_key = get_or_create_api_key(project_id)
        else:
            # Manual setup
            api_key = offer_manual_setup()
    else:
        print_info("\ngcloud CLI не знайдено. Використовується ручний режим.\n")
        api_key = offer_manual_setup()

    if api_key:
        update_env(api_key)
        print(f"\n{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
        print_success("Налаштування завершено успішно!")
        print_info("Перезапустіть додаток: npm run dev")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")
    else:
        print_error("Не вдалося отримати API ключ.")


if __name__ == "__main__":
    main()
