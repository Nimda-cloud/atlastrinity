import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.brain.voice.tts import VoiceManager, sanitize_text_for_tts


@pytest.fixture
def mock_config():
    with patch("src.brain.voice.tts.config") as mock:
        mock.get.return_value = {}  # Default return
        yield mock

@pytest.mark.asyncio
async def test_sanitize_text_for_tts():
    # Test 1: Markdown links
    text = "Check this [link](http://example.com) out."
    assert sanitize_text_for_tts(text) == "Check this link out."

    # Test 2: Code blocks
    text = "Code: ```python print('hello') ``` end."
    assert sanitize_text_for_tts(text) == "Code: end."

    # Test 3: Brackets (Thought traces)
    text = "[Thought 1]: Thinking process. Final answer."
    # Expect brackets removed
    assert sanitize_text_for_tts(text) == "Thought 1: Thinking process. Final answer."

    # Test 4: Abbreviations
    text = "Temp is 20°C"
    assert "градусів Цельсія" in sanitize_text_for_tts(text)

@pytest.mark.asyncio
async def test_prepare_speech_text(mock_config):
    # Setup VoiceManager
    vm = VoiceManager()

    # Mock translate_to_ukrainian
    vm.translate_to_ukrainian = AsyncMock(return_value="Перекладений текст")

    # Enable force_ukrainian
    mock_config.get.side_effect = lambda key, default=None: (
        True if key == "voice.tts.force_ukrainian" else default
    )

    # Test input
    text = "[Thought]: Internal reasoning"

    # Run
    result = await vm.prepare_speech_text(text)

    # Verification
    # 1. Sanitize should run first: "[Thought]: ..." -> "Thought: ..."
    # 2. Translate should receive "Thought: Internal reasoning"
    vm.translate_to_ukrainian.assert_called_once()
    assert result == "Перекладений текст"

@pytest.mark.asyncio
async def test_prepare_speech_text_no_translation(mock_config):
    # Setup VoiceManager
    vm = VoiceManager()
    vm.translate_to_ukrainian = AsyncMock()

    # Disable force_ukrainian
    mock_config.get.side_effect = lambda key, default=None: (
        False if key == "voice.tts.force_ukrainian" else default
    )

    text = "Hello world"
    result = await vm.prepare_speech_text(text)

    vm.translate_to_ukrainian.assert_not_called()
    assert result == "Hello world"
