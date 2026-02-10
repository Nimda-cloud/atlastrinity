#!/usr/bin/env python3
"""Simple Test for Request Segmentation (without LLM calls)"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.brain.request_segmenter import RequestSegment, RequestSegmenter


def test_keyword_segmentation():
    """Test keyword-based segmentation."""
    print("=== Test: Keyword Segmentation ===")
    
    segmenter = RequestSegmenter()
    
    # Test mixed request
    user_request = "Привіт! Як справи? Створи React компонент для калькулятора і знайди погоду у Львові"
    
    segments = segmenter._keyword_segmentation(user_request)
    
    print(f"Input: {user_request}")
    print(f"Segments found: {len(segments)}")
    
    for i, segment in enumerate(segments):
        print(f"\nSegment {i+1}:")
        print(f"  Text: {segment.text}")
        print(f"  Mode: {segment.mode}")
        print(f"  Priority: {segment.priority}")
        print(f"  Reason: {segment.reason}")
    
    # Should find at least 2 segments
    assert len(segments) >= 2, f"Expected at least 2 segments, got {len(segments)}"
    print("✅ Keyword segmentation test passed!")


def test_mode_priority():
    """Test mode priority ordering."""
    print("\n=== Test: Mode Priority Ordering ===")
    
    segmenter = RequestSegmenter()
    
    # Create segments with different priorities
    segments = [
        RequestSegment("text1", "task", priority=4),
        RequestSegment("text2", "chat", priority=1),
        RequestSegment("text3", "development", priority=5),
        RequestSegment("text4", "solo_task", priority=3),
    ]
    
    sorted_segments = segmenter._sort_and_merge_segments(segments)
    
    priorities = [s.priority for s in sorted_segments]
    print(f"Original priorities: {[s.priority for s in segments]}")
    print(f"Sorted priorities: {priorities}")
    
    # Should be sorted: [1, 3, 4, 5]
    assert priorities == sorted(priorities), "Segments not sorted correctly"
    print("✅ Priority ordering test passed!")


def test_mode_profiles_loading():
    """Test that mode profiles are loaded correctly."""
    print("\n=== Test: Mode Profiles Loading ===")
    
    from src.brain.request_segmenter import _MODE_PROFILES, _SEGMENTATION_CONFIG
    
    print(f"Loaded modes: {list(_MODE_PROFILES.keys())}")
    print(f"Segmentation enabled: {_SEGMENTATION_CONFIG.get('enabled')}")
    print(f"Max segments: {_SEGMENTATION_CONFIG.get('max_segments')}")
    
    # Should have all expected modes
    expected_modes = ["chat", "deep_chat", "solo_task", "task", "development"]
    for mode in expected_modes:
        assert mode in _MODE_PROFILES, f"Mode {mode} not loaded"
    
    # Should have segmentation config
    assert "enabled" in _SEGMENTATION_CONFIG, "Segmentation config missing"
    
    print("✅ Mode profiles loading test passed!")


def test_segment_profile_building():
    """Test building profiles for segments."""
    print("\n=== Test: Segment Profile Building ===")
    
    from src.brain.request_segmenter import _build_segment_profile
    
    # Test chat profile
    chat_profile = _build_segment_profile("chat", "Привіт!")
    print(f"Chat profile - Mode: {chat_profile.mode}, Tools: {chat_profile.tools_access}")
    
    assert chat_profile.mode == "chat"
    assert chat_profile.tools_access == "none"
    
    # Test development profile
    dev_profile = _build_segment_profile("development", "Створи компонент")
    print(f"Dev profile - Mode: {dev_profile.mode}, Tools: {dev_profile.tools_access}, Vibe: {dev_profile.use_vibe}")
    
    assert dev_profile.mode == "development"
    assert dev_profile.tools_access == "full"
    assert dev_profile.use_vibe == True
    
    print("✅ Segment profile building test passed!")


def main():
    """Run all simple segmentation tests."""
    print("🧪 Testing Request Segmentation (Simple Tests)")
    print("=" * 50)
    
    try:
        test_mode_profiles_loading()
        test_segment_profile_building()
        test_keyword_segmentation()
        test_mode_priority()
        
        print("\n" + "=" * 50)
        print("✅ All simple segmentation tests passed!")
        
        # Show stats
        from src.brain.request_segmenter import request_segmenter
        stats = request_segmenter.get_stats()
        print(f"\nSegmentation Stats: {stats}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
