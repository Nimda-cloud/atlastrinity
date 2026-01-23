import asyncio
import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from src.brain.agents.atlas import Atlas

# Configure logging to see Atlas output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brain.agents.atlas")

class TestAtlasChatLoop(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # We'll set up the mock LLM in the test method since we need it there
        pass

    @patch("src.brain.mcp_manager.mcp_manager")
    @patch("src.brain.behavior_engine.behavior_engine")
    async def test_chat_loop_preamble_and_synthesis(self, mock_behavior, mock_mcp):
        # Mock behavior engine to avoid real API calls
        mock_behavior.classify_intent.return_value = {"intent": "solo_task", "type": "complex"}
        
        # 1. Setup mock LLM
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock()
        mock_llm.bind_tools.return_value = mock_llm
        
        # Turn 1: Returns tool calls and a preamble
        turn_1_response = MagicMock()
        turn_1_response.content = "Зараз я перевірю погоду в Києві."
        turn_1_response.tool_calls = [{"id": "c1", "name": "weather_get", "args": {"location": "Kyiv"}}]
        
        # Turn 2: Returns final synthesized answer
        turn_2_response = MagicMock()
        turn_2_response.content = "У Києві зараз +5 градусів, хмарно."
        turn_2_response.tool_calls = None
        
        mock_llm.ainvoke.side_effect = [turn_1_response, turn_2_response]
        
        # Use the injected LLM in Atlas
        self.atlas = Atlas(llm=mock_llm)
        
        # 2. Setup mock MCP tool
        mock_mcp.dispatch_tool.return_value = {"temperature": 5, "condition": "Cloudy"}
        
        # 3. Setup preamble callback
        on_preamble_mock = AsyncMock()
        
        # 4. Run chat
        final_answer = await self.atlas.chat(
            "Яка погода в Києві?", 
            on_preamble=on_preamble_mock
        )
        
        # Give background tasks a moment to run
        await asyncio.sleep(0.5)
        
        # 5. Assertions
        print(f"DEBUG: Preamble mock called: {on_preamble_mock.called}")
        if on_preamble_mock.called:
             print(f"DEBUG: Preamble mock call args: {on_preamble_mock.call_args}")
        
        # Check preamble was called
        on_preamble_mock.assert_called()
        
        # Check final answer
        self.assertEqual(final_answer, "У Києві зараз +5 градусів, хмарно.")
        
        # Check that LLM was called twice
        self.assertEqual(mock_llm.ainvoke.call_count, 2)
        
        print("\n✅ Test passed: Preamble spoken and Turn 2 synthesized correctly.")

if __name__ == "__main__":
    unittest.main()
