
import asyncio
import os
import sys
from pathlib import Path

# Додаємо src до шляху, щоб знайти mcp_server
sys.path.append(os.path.join(os.getcwd(), "src"))

from mcp_server.vibe_server import _run_vibe

async def main():
    print("🚀 Запуск другої копії 'мозку' Вайба для тестування думок...")
    
    # Завдання: Створити файл і пояснити навіщо
    objective = "Створи файл 'thought_test.txt' з текстом 'Я думаю, отже я існую' і коротким поясненням що це тест паралельної роботи."
    
    print(f"📡 Відправка завдання: {objective}")
    
    # Викликаємо внутрішню функцію (вона логує в brain.log автоматично)
    result = await _run_vibe(
        argv=["vibe", "-p", objective, "--output", "streaming", "--auto-approve"],
        cwd=os.getcwd(),
        timeout_s=300,
        extra_env=None
    )
    
    if result.get("success"):
        print("✅ Успіх! Файл створено.")
    else:
        print(f"❌ Помилка: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
