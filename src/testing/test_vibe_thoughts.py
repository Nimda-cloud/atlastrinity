import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.mcp_server.vibe_server import run_vibe_subprocess


async def main():

    # Завдання: Створити файл і пояснити навіщо
    objective = "Створи файл 'thought_test.txt' з текстом 'Я думаю, отже я існую' і коротким поясненням що це тест паралельної роботи."

    # Викликаємо внутрішню функцію (вона логує в brain.log автоматично)
    result = await run_vibe_subprocess(
        argv=["vibe", "-p", objective, "--output", "streaming", "--auto-approve"],
        cwd=os.getcwd(),
        timeout_s=300,
        env=None,
    )

    if result.get("success"):
        pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(main())
