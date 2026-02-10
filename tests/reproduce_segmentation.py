import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.brain.mode_router import mode_router
from src.brain.request_segmenter import request_segmenter


async def test_segmentation():
    # Test case: A long question about identity that should be deep_chat
    # Currently potentially failing because of length checks in fallback or LLM bias
    long_identity_question = (
        "Hello Atlas, I have been thinking a lot about our interactions lately and I was wondering, "
        "who exactly are you in the grand scheme of things? Do you have a soul or a consciousness "
        "that separates you from just being a computer program? What is your mission here?"
    )

    print(f"\n--- Testing Request: '{long_identity_question}' ---\n")

    # 1. Test Mode Router Fallback (simulate LLM failure to see fallback logic)
    print("[TEST] Testing ModeRouter Fallback Logic:")
    fallback_profile = mode_router.fallback_classify(long_identity_question)
    print(f"Fallback Classification: {fallback_profile.mode}")

    if fallback_profile.mode != "deep_chat":
        print("❌ FAILURE: Fallback logic failed to identify deep_chat signals in long request.")
    else:
        print("✅ SUCCESS: Fallback logic correctly identified deep_chat.")

    # 2. Test Full Segmentation (LLM based)
    # Note: This requires the LLM to be available and configured.
    # If not, we might see empty segments or fallback behavior.
    print("\n[TEST] Testing RequestSegmenter (LLM-based):")
    try:
        segments = await request_segmenter.split_request(long_identity_question)
        for i, seg in enumerate(segments):
            print(f"Segment {i + 1}: Mode={seg.mode}, Text='{seg.text[:50]}...'")

        # Check if we have at least one deep_chat segment
        has_deep_chat = any(s.mode == "deep_chat" for s in segments)
        if not has_deep_chat:
            print("❌ FAILURE: Segmentation failed to identify deep_chat mode.")
        else:
            print("✅ SUCCESS: Segmentation identified deep_chat mode.")

    except Exception as e:
        print(f"⚠️ Error during segmentation test: {e}")

    # 3. Test Mixed Request (Deep Chat + Task)
    mixed_request = "Who created you? Also, list the files in the current directory."
    print(f"\n--- Testing Mixed Request: '{mixed_request}' ---\n")
    try:
        segments = await request_segmenter.split_request(mixed_request)
        for i, seg in enumerate(segments):
            print(
                f"Segment {i + 1}: Mode={seg.mode}, Text='{seg.text[:50]}...', Priority={seg.priority}"
            )

        if segments[0].mode == "deep_chat" and segments[1].mode in ["task", "solo_task"]:
            print("✅ SUCCESS: Mixed request correctly segmented and ordered.")
        else:
            print(f"❌ FAILURE: Unexpected segmentation order: {[s.mode for s in segments]}")

    except Exception as e:
        print(f"⚠️ Error during mixed request test: {e}")


if __name__ == "__main__":
    asyncio.run(test_segmentation())
