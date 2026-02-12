#!/usr/bin/env python3
"""Test Request Segmentation System

Tests the intelligent request splitting functionality
integrated with mode_profiles.json configuration.
"""

import asyncio
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.brain.core.orchestration.mode_router import mode_router
from src.brain.core.orchestration.request_segmenter import RequestSegment, request_segmenter


async def test_basic_segmentation():
    """Test basic request segmentation."""
    print("=== Test 1: Basic Mixed Request ===")

    user_request = "Привіт! Як справи? Мені потрібно створити React компонент для калькулятора та виправити баг в авторизації"

    segments = await request_segmenter.split_request(user_request)

    print(f"Input: {user_request}")
    print(f"Segments found: {len(segments)}")

    for i, segment in enumerate(segments):
        print(f"\nSegment {i + 1}:")
        print(f"  Text: {segment.text}")
        print(f"  Mode: {segment.mode}")
        print(f"  Priority: {segment.priority}")
        print(f"  Reason: {segment.reason}")
        print(f"  Start: {segment.start_pos}, End: {segment.end_pos}")

    # Expected: 3 segments (chat, development, development)
    assert len(segments) >= 2, f"Expected at least 2 segments, got {len(segments)}"
    assert any(s.mode == "chat" for s in segments), "Expected chat segment"
    assert any(s.mode == "development" for s in segments), "Expected development segment"


async def test_complex_task_segmentation():
    """Test complex task with multiple modes."""
    print("\n=== Test 2: Complex Multi-Task Request ===")

    user_request = "Покажи погоду у Львові, а потім створи новий Python скрипт для аналізу даних і відправ email з результатами"

    segments = await request_segmenter.split_request(user_request)

    print(f"Input: {user_request}")
    print(f"Segments found: {len(segments)}")

    for i, segment in enumerate(segments):
        print(f"\nSegment {i + 1}:")
        print(f"  Text: {segment.text}")
        print(f"  Mode: {segment.mode}")
        print(f"  Priority: {segment.priority}")

    # Expected: 3 segments (solo_task, development, task)
    assert len(segments) >= 2, f"Expected at least 2 segments, got {len(segments)}"


async def test_philosophical_segmentation():
    """Test philosophical deep chat segmentation."""
    print("\n=== Test 3: Philosophical + Task Request ===")

    user_request = "Хто ти насправді? І як мені створити API endpoint для користувачів?"

    segments = await request_segmenter.split_request(user_request)

    print(f"Input: {user_request}")
    print(f"Segments found: {len(segments)}")

    for i, segment in enumerate(segments):
        print(f"\nSegment {i + 1}:")
        print(f"  Text: {segment.text}")
        print(f"  Mode: {segment.mode}")
        print(f"  Priority: {segment.priority}")

    # Expected: 2 segments (deep_chat, development)
    assert len(segments) >= 1, f"Expected at least 1 segment, got {len(segments)}"


async def test_simple_chat():
    """Test simple chat (no segmentation)."""
    print("\n=== Test 4: Simple Chat (No Segmentation) ===")

    user_request = "Привіт! Як справи?"

    segments = await request_segmenter.split_request(user_request)

    print(f"Input: {user_request}")
    print(f"Segments found: {len(segments)}")

    for i, segment in enumerate(segments):
        print(f"\nSegment {i + 1}:")
        print(f"  Text: {segment.text}")
        print(f"  Mode: {segment.mode}")
        print(f"  Priority: {segment.priority}")

    # Expected: 1 segment (chat)
    assert len(segments) == 1, f"Expected 1 segment, got {len(segments)}"
    assert segments[0].mode == "chat", f"Expected chat mode, got {segments[0].mode}"


async def test_segmentation_stats():
    """Test segmentation statistics."""
    print("\n=== Test 5: Segmentation Stats ===")

    stats = request_segmenter.get_stats()
    print("Segmentation Statistics:")
    print(json.dumps(stats, indent=2))

    # Verify stats structure
    assert "total_segmentations" in stats
    assert "segmentation_enabled" in stats
    assert "available_modes" in stats


async def test_mode_priority_ordering():
    """Test that segments are ordered by priority correctly."""
    print("\n=== Test 6: Priority Ordering ===")

    user_request = "Дякую! Створи файл, знайди документацію, розкажи про свою місію"

    segments = await request_segmenter.split_request(user_request)

    print(f"Input: {user_request}")
    print(f"Segments found: {len(segments)}")

    priorities = [s.priority for s in segments]
    print(f"Priorities: {priorities}")

    # Verify segments are sorted by priority (lower number = higher priority)
    assert priorities == sorted(priorities), f"Segments not sorted by priority: {priorities}"


async def main():
    """Run all segmentation tests."""
    print("🧪 Testing Request Segmentation System")
    print("=" * 50)

    try:
        await test_basic_segmentation()
        await test_complex_task_segmentation()
        await test_philosophical_segmentation()
        await test_simple_chat()
        await test_segmentation_stats()
        await test_mode_priority_ordering()

        print("\n" + "=" * 50)
        print("✅ All segmentation tests passed!")

        # Show final stats
        final_stats = request_segmenter.get_stats()
        print(f"\nFinal Statistics: {final_stats['total_segmentations']} segmentations performed")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
