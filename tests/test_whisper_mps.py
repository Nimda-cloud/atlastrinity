#!/usr/bin/env python3
"""Test Whisper STT з різними devices (MPS vs CPU)

Перевіряє:
1. Чи доступний MPS (Apple Silicon GPU)
2. Чи працює Whisper на MPS
3. Порівняння швидкості MPS vs CPU
"""

import sys
import time
from pathlib import Path

import pytest
import torch

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.brain.config_loader import config
from src.brain.voice.stt import WhisperSTT


def check_mps_availability():
    """Перевіряє чи доступний MPS"""
    print("\n" + "=" * 60)
    print("🔍 ПЕРЕВІРКА MPS (Apple Silicon GPU)")
    print("=" * 60)

    if torch.backends.mps.is_available():
        print("✅ MPS доступний!")
        print(f"   PyTorch version: {torch.__version__}")

        if torch.backends.mps.is_built():
            print("✅ PyTorch скомпільовано з MPS підтримкою")
        else:
            print("⚠️  PyTorch НЕ скомпільовано з MPS")
            return False

        return True
    print("❌ MPS недоступний")
    print("   Ви НЕ на Apple Silicon Mac, або PyTorch застарілий")
    return False


def test_whisper_device(device_name: str):
    """Тестує Whisper на вказаному device"""
    print(f"\n{'=' * 60}")
    print(f"🧪 ТЕСТ WHISPER НА {device_name.upper()}")
    print(f"{'=' * 60}")

    try:
        start = time.time()

        # Створюємо WhisperSTT з вказаним device
        print(f"Ініціалізація WhisperSTT(device='{device_name}')...")
        stt = WhisperSTT(device=device_name)

        init_time = time.time() - start
        print(f"✓ Ініціалізація: {init_time:.2f}s")
        print(f"  Model: {stt.model_name}")
        print(f"  Device: {stt.device}")
        print(f"  Language: {stt.language}")
        print(f"  Download root: {stt.download_root}")

        # Завантажуємо модель (lazy load)
        print(f"\nЗавантаження моделі '{stt.model_name}'...")
        load_start = time.time()

        # Trigger model loading (WhisperSTT uses async get_model)
        import asyncio as _asyncio

        _model = _asyncio.run(stt.get_model())

        load_time = time.time() - load_start
        print(f"✓ Модель завантажена: {load_time:.2f}s")

        # Перевіряємо чи модель дійсно на потрібному device
        if hasattr(stt._model, "device"):
            actual_device = str(stt._model.device)
            print(f"  Фактичний device моделі: {actual_device}")

        total_time = time.time() - start
        print("\n✅ ТЕСТ ПРОЙДЕНО!")
        print(f"   Загальний час: {total_time:.2f}s")

        # Return status for comparison
        return {"success": True, "total_time": total_time}

    except Exception as e:
        print(f"\n❌ ПОМИЛКА: {e}")
        import traceback

        traceback.print_exc()

        pytest.fail(f"Whisper test failed on {device_name}: {e}")


def main():
    print("\n" + "=" * 60)
    print("🎯 WHISPER MPS TEST")
    print("=" * 60)

    # Читаємо конфіг
    stt_config = config.get("voice.stt", {})
    print("\n📋 Config:")
    print(f"   Model: {stt_config.get('model', 'base')}")
    print(f"   Language: {stt_config.get('language', 'uk')}")
    print(f"   Device: {stt_config.get('device', 'cpu')}")

    # 1. Перевіряємо MPS
    mps_available = check_mps_availability()

    # 2. Тестуємо CPU (baseline)
    cpu_result = test_whisper_device("cpu") or {"success": False, "total_time": 0}

    # 3. Тестуємо MPS (якщо доступний)
    if mps_available:
        mps_result = test_whisper_device("mps") or {"success": False, "total_time": 0}

        # Порівняння
        if cpu_result.get("success") and mps_result.get("success"):
            print("\n" + "=" * 60)
            print("📊 ПОРІВНЯННЯ CPU vs MPS")
            print("=" * 60)

            cpu_total = cpu_result.get("total_time") or 0.0
            mps_total = mps_result.get("total_time") or 0.1  # avoid div by zero
            speedup = cpu_total / mps_total if mps_total > 0 else 0

            print(f"\nCPU:  {cpu_total:.2f}s")
            print(f"MPS:  {mps_total:.2f}s")
            print(f"\n{'⚡ MPS швидший' if speedup > 1 else '🐌 CPU швидший'}: {speedup:.2f}x")

            if speedup > 1:
                print("\n✅ РЕКОМЕНДАЦІЯ: Використовуйте device: 'mps' в config.yaml")
            else:
                print("\n⚠️  РЕКОМЕНДАЦІЯ: device: 'cpu' може бути кращим варіантом")
    else:
        mps_result = {"success": False}
        print("\n⚠️  MPS недоступний - пропускаємо тест")
        print("   Використовуйте device: 'cpu' в config.yaml")

    # Фінальний висновок
    print("\n" + "=" * 60)
    print("📝 ВИСНОВОК")
    print("=" * 60)

    if mps_available and mps_result.get("success"):
        print("\n✅ Whisper працює на MPS (Apple Silicon GPU)")
        print("   Рекомендується для прискорення транскрипції")
        print("\n📝 Додайте в config.yaml:")
        print("   voice:")
        print("     stt:")
        print("       device: 'mps'")
    else:
        print("\n⚠️  Використовуйте CPU для Whisper")
        print("\n📝 Config.yaml:")
        print("   voice:")
        print("     stt:")
        print("       device: 'cpu'")

    print(f"\n{'=' * 60}\n")


if __name__ == "__main__":
    main()
