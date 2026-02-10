"""Request Segmenter — Intelligent Multi-Mode Request Splitting

Splits mixed user requests into separate mode-specific segments for optimal processing.
Integrates with mode_profiles.json configuration for declarative segmentation rules.

Architecture:
    1. LLM analyzes request structure and intent segments
    2. Mode profiles provide segmentation rules and priorities
    3. Segments are ordered by priority and execution context
    4. Each segment gets its own ModeProfile for processing

Usage:
    from src.brain.request_segmenter import request_segmenter

    segments = await request_segmenter.split_request(user_request, history, context)
    # Returns list of RequestSegment objects
"""

import json
import os
from dataclasses import dataclass
from typing import Any

from .logger import logger
from .mode_router import ModeProfile, ModeRouter

# Load mode profiles for segmentation rules
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_PROFILES_PATH = os.path.join(_DATA_DIR, "mode_profiles.json")

_MODE_PROFILES: dict[str, Any] = {}
_SEGMENTATION_CONFIG: dict[str, Any] = {}


def _load_profiles() -> None:
    """Load mode profiles and segmentation config."""
    global _MODE_PROFILES, _SEGMENTATION_CONFIG
    try:
        if os.path.exists(_PROFILES_PATH):
            with open(_PROFILES_PATH, encoding="utf-8") as f:
                data = json.load(f)

            _SEGMENTATION_CONFIG = data.get("_meta", {}).get("segmentation", {})
            data.pop("_meta", None)
            data.pop("_protocol_registry", None)
            _MODE_PROFILES = data
            logger.info(
                f"[SEGMENTER] Loaded segmentation config: enabled={_SEGMENTATION_CONFIG.get('enabled')}"
            )
        else:
            logger.warning(f"[SEGMENTER] Profiles not found at {_PROFILES_PATH}")
            # Set default config
            _SEGMENTATION_CONFIG = {"enabled": False, "max_segments": 5}
    except Exception as e:
        logger.error(f"[SEGMENTER] Failed to load profiles: {e}")
        # Set default config on error
        _SEGMENTATION_CONFIG = {"enabled": False, "max_segments": 5}


_load_profiles()


@dataclass
class RequestSegment:
    """Single segment of a split request with its mode profile."""

    text: str
    mode: str
    priority: int
    reason: str = ""
    start_pos: int = 0
    end_pos: int = 0
    profile: ModeProfile | None = None

    def __post_init__(self) -> None:
        """Create profile from mode if not provided."""
        if self.profile is None:
            self.profile = _build_segment_profile(self.mode, self.text)


def _build_segment_profile(mode: str, text: str) -> ModeProfile:
    """Build ModeProfile for a segment using mode defaults."""
    defaults = _MODE_PROFILES.get(mode, _MODE_PROFILES.get("chat", {}))

    return ModeProfile(
        mode=mode,
        reason=f"Segmented request: {text[:50]}...",
        enriched_request=text,
        complexity=defaults.get("complexity", "medium"),
        llm_tier=defaults.get("llm_tier", "standard"),
        protocols=list(defaults.get("protocols", [])),
        servers=list(defaults.get("servers", [])),
        tools_access=defaults.get("tools_access", "none"),
        prompt_template=defaults.get("prompt_template", "atlas_chat"),
        require_planning=defaults.get("require_planning", False),
        require_tools=defaults.get("require_tools", False),
        use_deep_persona=defaults.get("use_deep_persona", False),
        use_sequential_thinking=defaults.get("use_sequential_thinking", False),
        use_vibe=defaults.get("use_vibe", False),
        trinity_required=defaults.get("trinity_required", False),
    )


class RequestSegmenter:
    """Intelligent request segmentation using LLM + mode profile rules."""

    def __init__(self) -> None:
        self.mode_router = ModeRouter()
        self._segmentation_count = 0
        self._fallback_count = 0

    async def split_request(
        self,
        user_request: str,
        history: list[Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[RequestSegment]:
        """Split user request into mode-specific segments.

        Args:
            user_request: Full user request text
            history: Conversation history for context
            context: Additional context information

        Returns:
            List of RequestSegment objects ordered by execution priority
        """
        self._segmentation_count += 1

        # Check if segmentation is enabled
        if not _SEGMENTATION_CONFIG.get("enabled", False):
            # Return single segment with full request
            profile = await self._classify_full_request(user_request, history, context)
            return [
                RequestSegment(
                    text=user_request,
                    mode=profile.mode,
                    priority=1,
                    reason="Segmentation disabled",
                    profile=profile,
                )
            ]

        # Try LLM-based segmentation first
        try:
            segments = await self._llm_segmentation(user_request, history, context)
            if segments:
                logger.info(f"[SEGMENTER] LLM segmentation: {len(segments)} segments")
                return self._sort_and_merge_segments(segments)
        except Exception as e:
            logger.warning(f"[SEGMENTER] LLM segmentation failed: {e}")

        # Fallback to keyword-based segmentation
        self._fallback_count += 1
        segments = self._keyword_segmentation(user_request)
        logger.info(f"[SEGMENTER] Keyword fallback: {len(segments)} segments")
        return self._sort_and_merge_segments(segments)

    async def _llm_segmentation(
        self,
        user_request: str,
        history: list[Any] | None,
        context: dict[str, Any] | None,
    ) -> list[RequestSegment]:
        """Use LLM to intelligently split request into segments."""

        # Build segmentation prompt
        prompt = self._build_segmentation_prompt(user_request, history, context)

        # Import here to avoid circular imports
        from .agents.atlas import Atlas

        # Use standard LLM for segmentation (not deep persona)
        atlas = Atlas()
        system_prompt = """You are a request segmentation expert. Analyze the user's request and split it into logical segments by intent mode.

Available modes:
- chat: Simple greetings, small talk, thanks, acknowledgments (1-6 words)
- deep_chat: Philosophical, identity, mission, soul, consciousness topics
- solo_task: Research, lookup, info retrieval with tools (weather, search, read files)
- task: Direct execution requiring planning and tools (create, open, install, send)
- development: Software development, coding, debugging, testing

Rules:
1. Split mixed requests into separate segments
2. Each segment should have one clear intent
3. Preserve original wording and context
4. Order segments logically
5. Minimum 3 words per segment (except chat)

Return JSON format:
{
  "segments": [
    {
      "text": "segment text",
      "mode": "mode_name", 
      "reason": "why this mode",
      "start_pos": 0,
      "end_pos": 15
    }
  ]
}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await atlas.llm.ainvoke(messages)
            result = json.loads(response.content)

            segments = []
            for seg_data in result.get("segments", []):
                segment = RequestSegment(
                    text=seg_data.get("text", ""),
                    mode=seg_data.get("mode", "chat"),
                    priority=self._get_mode_priority(seg_data.get("mode", "chat")),
                    reason=seg_data.get("reason", ""),
                    start_pos=seg_data.get("start_pos", 0),
                    end_pos=seg_data.get("end_pos", 0),
                )
                segments.append(segment)

            return segments

        except Exception as e:
            logger.error(f"[SEGMENTER] LLM segmentation parsing failed: {e}")
            return []

    def _build_segmentation_prompt(
        self,
        user_request: str,
        history: list[Any] | None,
        context: dict[str, Any] | None,
    ) -> str:
        """Build prompt for LLM segmentation."""

        prompt_parts = [
            f"User Request: {user_request}",
        ]

        if history:
            prompt_parts.append(f"Recent History: {history[-3:]!s}")

        if context:
            prompt_parts.append(f"Context: {context!s}")

        prompt_parts.extend(
            [
                "",
                "Split this request into logical segments by intent mode.",
                "Consider mixed requests like greetings + tasks, or multiple different task types.",
                "Each segment should be processed with its optimal mode.",
            ]
        )

        return "\n".join(prompt_parts)

    def _keyword_segmentation(self, user_request: str) -> list[RequestSegment]:
        """Fallback keyword-based segmentation using mode profiles."""

        segments = []
        words = user_request.split()
        current_segment = []
        current_mode: str | None = None
        current_start = 0

        for i, word in enumerate(words):
            word_lower = word.lower()

            # Check each mode's split keywords
            detected_mode: str | None = None
            for mode_name, mode_config in _MODE_PROFILES.items():
                seg_config = mode_config.get("segmentation", {})
                split_keywords = seg_config.get("split_keywords", [])

                if any(keyword in word_lower for keyword in split_keywords):
                    detected_mode = mode_name
                    break

            # If mode changed, create segment
            if detected_mode and detected_mode != current_mode and current_segment:
                # Save previous segment
                segment_text = " ".join(current_segment)
                if len(segment_text.strip()) >= _SEGMENTATION_CONFIG.get("min_segment_length", 3):
                    segments.append(
                        RequestSegment(
                            text=segment_text,
                            mode=current_mode or "chat",
                            priority=self._get_mode_priority(current_mode or "chat"),
                            reason=f"Keyword detection: {current_mode}",
                            start_pos=current_start,
                            end_pos=current_start + len(segment_text),
                        )
                    )

                current_segment = [word]
                current_mode = detected_mode
                current_start = len(" ".join(words[:i]))
            else:
                current_segment.append(word)
                if not current_mode and detected_mode:
                    current_mode = detected_mode

        # Add final segment
        if current_segment:
            segment_text = " ".join(current_segment)
            if len(segment_text.strip()) >= _SEGMENTATION_CONFIG.get("min_segment_length", 3):
                segments.append(
                    RequestSegment(
                        text=segment_text,
                        mode=current_mode or "chat",
                        priority=self._get_mode_priority(current_mode or "chat"),
                        reason=f"Keyword detection: {current_mode}",
                        start_pos=current_start,
                        end_pos=len(user_request),
                    )
                )

        return segments or [
            RequestSegment(
                text=user_request, mode="chat", priority=1, reason="No segmentation detected"
            )
        ]

    def _get_mode_priority(self, mode: str) -> int:
        """Get priority from mode profile segmentation config."""
        mode_config = _MODE_PROFILES.get(mode, {})
        seg_config = mode_config.get("segmentation", {})
        return seg_config.get("priority", 999)

    def _sort_and_merge_segments(self, segments: list[RequestSegment]) -> list[RequestSegment]:
        """Sort segments by priority and merge compatible segments."""

        # Sort by priority (lower number = higher priority)
        segments.sort(key=lambda s: s.priority)

        # Merge consecutive segments of same mode
        merged = []
        i = 0
        while i < len(segments):
            current = segments[i]

            # Look for merge candidates
            mode_config = _MODE_PROFILES.get(current.mode, {})
            seg_config = mode_config.get("segmentation", {})
            merge_with = seg_config.get("merge_with", [])

            # Check if next segment can be merged
            if i + 1 < len(segments) and segments[i + 1].mode in merge_with:
                # Merge with next segment
                next_seg = segments[i + 1]
                merged_text = f"{current.text} {next_seg.text}".strip()

                merged.append(
                    RequestSegment(
                        text=merged_text,
                        mode=current.mode,
                        priority=current.priority,
                        reason=f"Merged {current.mode}+{next_seg.mode}",
                        start_pos=current.start_pos,
                        end_pos=next_seg.end_pos,
                    )
                )
                i += 2  # Skip both segments
            else:
                merged.append(current)
                i += 1

        # Limit number of segments
        max_segments = _SEGMENTATION_CONFIG.get("max_segments", 5)
        if len(merged) > max_segments:
            logger.warning(
                f"[SEGMENTER] Too many segments ({len(merged)}), limiting to {max_segments}"
            )
            # Keep highest priority segments
            merged = merged[:max_segments]

        return merged

    async def _classify_full_request(
        self,
        user_request: str,
        history: list[Any] | None,
        context: dict[str, Any] | None,
    ) -> ModeProfile:
        """Classify full request without segmentation (fallback)."""

        # Use existing Atlas analyze_request
        from .agents.atlas import Atlas

        atlas = Atlas()
        analysis = await atlas.analyze_request(user_request, context, history)
        return analysis.get("mode_profile", self.mode_router.build_profile({"mode": "chat"}))

    def get_stats(self) -> dict[str, Any]:
        """Segmentation statistics."""
        return {
            "total_segmentations": self._segmentation_count,
            "fallback_segmentations": self._fallback_count,
            "fallback_rate_pct": (
                round(self._fallback_count / self._segmentation_count * 100, 2)
                if self._segmentation_count > 0
                else 0
            ),
            "segmentation_enabled": _SEGMENTATION_CONFIG.get("enabled", False),
            "available_modes": list(_MODE_PROFILES.keys()),
        }


# Global singleton
request_segmenter = RequestSegmenter()
