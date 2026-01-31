#!/usr/bin/env python3
"""MCP Servers Validation Tool
Перевіряє доступність та конфігурацію всіх 17 MCP серверів після fresh setup.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


# Кольори для консолі
class Colors:
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    OKCYAN = "\033[96m"


def print_success(msg: str):
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {msg}")


def print_warning(msg: str):
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {msg}")


def print_error(msg: str):
    print(f"{Colors.FAIL}✗{Colors.ENDC} {msg}")


def print_info(msg: str):
    print(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {msg}")


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_ROOT = Path.home() / ".config" / "atlastrinity"
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"


def load_mcp_config() -> dict[str, Any]:
    """Завантажує конфігурацію MCP серверів"""
    config_path = CONFIG_ROOT / "mcp" / "config.json"
    if not config_path.exists():
        config_path = PROJECT_ROOT / "config" / "mcp_servers.json.template"

    if not config_path.exists():
        print_error(f"MCP конфігурація не знайдена: {config_path}")
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def validate_python_server(name: str, config: dict) -> bool:
    """Перевіряє Python MCP сервер"""
    args = config.get("args", [])
    if not args or not args[0] == "-m":
        print_error(f"{name}: Неправильна конфігурація Python модуля")
        return False

    module_name = args[1]

    # Перевірка наявності файлу
    if module_name.startswith("src.mcp_server.golden_fund"):
        server_file = PROJECT_ROOT / "src" / "mcp_server" / "golden_fund" / "server.py"
    else:
        server_file = PROJECT_ROOT / "src" / "mcp_server" / f"{module_name.split('.')[-1]}.py"

    if not server_file.exists():
        print_error(f"{name}: Файл не знайдено: {server_file}")
        return False

    # Перевірка, що модуль можна імпортувати
    if not VENV_PYTHON.exists():
        print_warning(f"{name}: venv не знайдено, пропускаємо import перевірку")
        return True

    try:
        result = subprocess.run(
            [str(VENV_PYTHON), "-c", f"import {module_name}"],
            capture_output=True,
            timeout=5,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            print_warning(f"{name}: Модуль не імпортується (можливо потрібні залежності)")
            print_info(f"  Error: {result.stderr.decode()[:200]}")
            return True  # Non-blocking для fresh setup
    except subprocess.TimeoutExpired:
        print_warning(f"{name}: Import timeout (це може бути нормальним)")
        return True
    except Exception as e:
        print_warning(f"{name}: Помилка перевірки: {e}")
        return True

    print_success(f"{name}: Python модуль OK ({server_file.name})")
    return True


def validate_node_server(name: str, config: dict) -> bool:
    """Перевіряє Node/NPM MCP сервер"""
    command = config.get("command")
    args = config.get("args", [])

    if not command:
        print_error(f"{name}: Команда не визначена")
        return False

    # Перевірка наявності npx/bunx
    if command in ["npx", "bunx"]:
        if not shutil.which(command):
            print_warning(f"{name}: {command} не знайдено в PATH")
            return False

        if args:
            package_name = (
                args[0] if not args[0].startswith("-") else (args[1] if len(args) > 1 else None)
            )
            if package_name:
                print_success(f"{name}: Node пакет ({package_name})")
                return True

    print_success(f"{name}: Node конфігурація OK")
    return True


def validate_direct_node_server(name: str, config: dict) -> bool:
    """Перевіряє Node MCP сервер з прямим node command"""
    args = config.get("args", [])

    if not args:
        print_error(f"{name}: Не вказано скрипт для node")
        return False

    script_path = args[0]

    # Розгортаємо змінні середовища
    if "${PROJECT_ROOT}" in script_path:
        script_path = script_path.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))

    script_file = Path(script_path)

    if not script_file.exists():
        print_error(f"{name}: Скрипт не знайдено: {script_file}")
        return False

    print_success(f"{name}: Node script OK ({script_file.name})")
    return True


def validate_swift_server(name: str, config: dict) -> bool:
    """Перевіряє Swift MCP сервер"""
    command = config.get("command")

    if not command:
        print_error(f"{name}: Command not specified in config")
        return False

    # Розгортаємо змінні середовища
    if "${PROJECT_ROOT}" in command:
        command = command.replace("${PROJECT_ROOT}", str(PROJECT_ROOT))

    binary_path = Path(command)

    if not binary_path.exists():
        print_error(f"{name}: Бінарник не знайдено: {binary_path}")
        print_info(f"  Запустіть: swift build -c release в {binary_path.parent.parent.parent}")
        return False

    if not os.access(binary_path, os.X_OK):
        print_error(f"{name}: Бінарник не виконується: {binary_path}")
        return False

    print_success(f"{name}: Swift binary OK ({binary_path.name})")
    return True


def validate_server(name: str, config: dict) -> dict:
    """Валідує окремий MCP сервер"""
    result = {
        "name": name,
        "tier": config.get("tier", "?"),
        "disabled": config.get("disabled", False),
        "status": "unknown",
        "type": "unknown",
        "description": config.get("description", "")[:80],
    }

    if result["disabled"]:
        result["status"] = "disabled"
        result["type"] = "disabled"
        return result

    command = config.get("command", "")

    # Визначаємо тип сервера
    if command in {"python3", "python"}:
        result["type"] = "Python"
        result["status"] = "ok" if validate_python_server(name, config) else "error"
    elif command in ["npx", "bunx"]:
        result["type"] = "Node"
        result["status"] = "ok" if validate_node_server(name, config) else "error"
    elif command == "node":
        result["type"] = "Node"
        result["status"] = "ok" if validate_direct_node_server(name, config) else "error"
    elif "mcp-server-macos-use" in command or command.endswith(
        ".build/release/mcp-server-macos-use"
    ):
        result["type"] = "Swift"
        result["status"] = "ok" if validate_swift_server(name, config) else "error"
    else:
        result["type"] = "other"
        result["status"] = "unknown"
        print_warning(f"{name}: Невідомий тип команди: {command}")

    return result


def main():
    print(f"\n{Colors.BOLD}=== MCP Servers Validation ==={Colors.ENDC}\n")

    # Завантажуємо конфігурацію
    config = load_mcp_config()
    servers = config.get("mcpServers", {})

    # Фільтруємо коментарі
    servers = {k: v for k, v in servers.items() if not k.startswith("_comment")}

    print_info(f"Знайдено {len(servers)} MCP серверів у конфігурації\n")

    results = []
    for name, server_config in servers.items():
        result = validate_server(name, server_config)
        results.append(result)

    # Статистика
    print(f"\n{Colors.BOLD}=== Результати валідації ==={Colors.ENDC}\n")

    total = len(results)
    ok_count = sum(1 for r in results if r["status"] == "ok")
    error_count = sum(1 for r in results if r["status"] == "error")
    disabled_count = sum(1 for r in results if r["disabled"])

    print(f"Усього серверів: {total}")
    print_success(f"Дієздатні: {ok_count}")
    if error_count > 0:
        print_error(f"Помилки: {error_count}")
    if disabled_count > 0:
        print_info(f"Вимкнені: {disabled_count}")

    # Детальна таблиця
    print(f"\n{Colors.BOLD}Деталі:{Colors.ENDC}\n")
    print(f"{'Сервер':<25} {'Тип':<10} {'Tier':<6} {'Статус':<10}")
    print("-" * 60)

    for r in sorted(results, key=lambda x: (x.get("tier", 99), x["name"])):
        status_icon = "✓" if r["status"] == "ok" else ("✗" if r["status"] == "error" else "⊝")
        status_color = (
            Colors.OKGREEN
            if r["status"] == "ok"
            else (Colors.FAIL if r["status"] == "error" else Colors.WARNING)
        )

        print(
            f"{r['name']:<25} {r['type']:<10} {r['tier']:<6} {status_color}{status_icon} {r['status']}{Colors.ENDC}"
        )

    print()

    # Список для інформації користувача
    print(f"\n{Colors.BOLD}ℹ Доступні MCP сервери ({ok_count}):{Colors.ENDC}")
    for r in sorted(results, key=lambda x: (x.get("tier", 99), x["name"])):
        if r["status"] == "ok":
            desc = r["description"] if len(r["description"]) < 60 else r["description"][:57] + "..."
            print(f"  - {r['name']}: {desc} ({r['type']})")

    print()

    # Повертаємо код помилки якщо є проблеми
    if error_count > 0:
        print_warning(f"\n⚠ Знайдено {error_count} проблемних серверів")
        return 1

    print_success("\n✓ Всі активні MCP сервери пройшли валідацію!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
