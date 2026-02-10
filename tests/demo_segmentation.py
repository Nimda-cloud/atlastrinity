#!/usr/bin/env python3
"""Demo: Request Segmentation in Action

Shows how the system intelligently splits mixed requests
into optimal mode segments for processing.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.brain.request_segmenter import request_segmenter


def demo_mixed_request():
    """Demo: Mixed chat + development + task request."""
    print("🎯 Demo 1: Mixed Request Segmentation")
    print("=" * 50)
    
    user_request = "Привіт! Як справи? Мені потрібно створити React компонент для калькулятора, виправити баг в модулі авторизації і відправ email з результатами"
    
    print(f"📝 Input Request:")
    print(f"   {user_request}")
    print()
    
    # This would normally use LLM, but we'll use keyword fallback for demo
    segments = request_segmenter._keyword_segmentation(user_request)
    
    print(f"🔍 Segmentation Results:")
    print(f"   Found {len(segments)} segments")
    print()
    
    for i, segment in enumerate(segments, 1):
        print(f"   Segment {i}: [{segment.mode.upper()}]")
        print(f"   ├─ Text: '{segment.text}'")
        print(f"   ├─ Priority: {segment.priority}")
        print(f"   └─ Reason: {segment.reason}")
        print()
    
    print("💡 How this would be processed:")
    print("   1. Chat segment → Simple response (no tools)")
    print("   2. Development segment → Vibe + Trinity planning")
    print("   3. Development segment → Vibe + Trinity planning") 
    print("   4. Task segment → Trinity planning")
    print()


def demo_philosophical_task():
    """Demo: Philosophical + development request."""
    print("🎯 Demo 2: Philosophical + Development")
    print("=" * 50)
    
    user_request = "Хто ти насправді? І як мені створити API endpoint для користувачів з аутентифікацією?"
    
    print(f"📝 Input Request:")
    print(f"   {user_request}")
    print()
    
    segments = request_segmenter._keyword_segmentation(user_request)
    
    print(f"🔍 Segmentation Results:")
    print(f"   Found {len(segments)} segments")
    print()
    
    for i, segment in enumerate(segments, 1):
        print(f"   Segment {i}: [{segment.mode.upper()}]")
        print(f"   ├─ Text: '{segment.text}'")
        print(f"   ├─ Priority: {segment.priority}")
        print(f"   └─ Reason: {segment.reason}")
        print()
    
    print("💡 How this would be processed:")
    print("   1. Deep Chat segment → Deep persona + memory")
    print("   2. Development segment → Vibe + Trinity planning")
    print()


def demo_simple_chat():
    """Demo: Simple chat (no segmentation needed)."""
    print("🎯 Demo 3: Simple Chat (No Segmentation)")
    print("=" * 50)
    
    user_request = "Привіт! Як справи?"
    
    print(f"📝 Input Request:")
    print(f"   {user_request}")
    print()
    
    segments = request_segmenter._keyword_segmentation(user_request)
    
    print(f"🔍 Segmentation Results:")
    print(f"   Found {len(segments)} segments")
    print()
    
    for i, segment in enumerate(segments, 1):
        print(f"   Segment {i}: [{segment.mode.upper()}]")
        print(f"   ├─ Text: '{segment.text}'")
        print(f"   ├─ Priority: {segment.priority}")
        print(f"   └─ Reason: {segment.reason}")
        print()
    
    print("💡 How this would be processed:")
    print("   Single segment → Direct chat response (no tools, no planning)")
    print()


def demo_configuration():
    """Show current segmentation configuration."""
    print("⚙️  Current Segmentation Configuration")
    print("=" * 50)
    
    from src.brain.request_segmenter import _SEGMENTATION_CONFIG, _MODE_PROFILES
    
    print(f"🔧 Segmentation Settings:")
    print(f"   Enabled: {_SEGMENTATION_CONFIG.get('enabled')}")
    print(f"   Strategy: {_SEGMENTATION_CONFIG.get('split_strategy')}")
    print(f"   Max Segments: {_SEGMENTATION_CONFIG.get('max_segments')}")
    print(f"   Min Segment Length: {_SEGMENTATION_CONFIG.get('min_segment_length')}")
    print()
    
    print(f"📋 Available Modes:")
    for mode_name, mode_config in _MODE_PROFILES.items():
        seg_config = mode_config.get("segmentation", {})
        print(f"   • {mode_name}:")
        print(f"     ├─ Priority: {seg_config.get('priority', 'N/A')}")
        print(f"     ├─ Keywords: {len(seg_config.get('split_keywords', []))} defined")
        print(f"     └─ Can merge with: {seg_config.get('merge_with', [])}")
    print()


def main():
    """Run all demos."""
    print("🚀 AtlasTrinity Request Segmentation Demo")
    print("=" * 60)
    print()
    
    demo_configuration()
    demo_simple_chat()
    demo_mixed_request()
    demo_philosophical_task()
    
    print("✅ Demo completed!")
    print()
    print("📊 Final Statistics:")
    stats = request_segmenter.get_stats()
    print(f"   Total segmentations: {stats['total_segmentations']}")
    print(f"   Segmentation enabled: {stats['segmentation_enabled']}")
    print(f"   Available modes: {len(stats['available_modes'])}")


if __name__ == "__main__":
    main()
