import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.memory import long_term_memory


async def cleanup(total_wipe=False):

    # 1. Delete specific hallucinations
    hallucinations = [
        "Сподівайся, як обходить",
        "я не маю прямого доступу до актуальних метеорологічних даних",
        "я не можу надати точний прогноз погоди",
        "нажаль я не маю доступу",
        "не маю доступу до інтернет",
        "я не маю прямого доступу до інтернету",
    ]

    for h in hallucinations:
        deleted = await long_term_memory.delete_specific_memory("conversations", h)
        if deleted:
            pass

        deleted_lessons = await long_term_memory.delete_specific_memory("lessons", h)
        if deleted_lessons:
            pass

    # 2. Clear all learning (if flag is set)
    if total_wipe:
        success = await long_term_memory.clear_all_memory()
        if success:
            pass
        else:
            pass
    else:
        pass


if __name__ == "__main__":
    total = "--total" in sys.argv
    asyncio.run(cleanup(total_wipe=total))
