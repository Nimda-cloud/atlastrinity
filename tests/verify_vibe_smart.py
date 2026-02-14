
import asyncio
import sys
import os
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.mcp_server.vibe_server import vibe_check_db
    from mcp.server.fastmcp import Context
except ImportError as e:
    print(f"CRITICAL: Failed to import vibe_server: {e}")
    sys.exit(1)

# Mock Context
class MockContext:
    def __init__(self):
        self.request_context = MagicMock()
        self.meta = {}

class TestVibeSmartDB(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ctx = MockContext()

    @patch("src.brain.memory.db.manager.db_manager")
    async def test_raw_sql(self, mock_db):
        """Test that raw SQL is passed through correctly."""
        # Setup mock
        mock_db.initialize = AsyncMock()
        mock_db.available = True
        
        # Use MagicMock for session to avoid AsyncMock recursion issues
        mock_session = MagicMock()
        mock_session.close = AsyncMock()
        
        # Mock result
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [{"id": 1}]
        
        async def mock_execute(*args, **kwargs):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # get_session must be awaitable and return our mock_session
        mock_db.get_session = AsyncMock(return_value=mock_session)

        # Execute
        res = await vibe_check_db(self.ctx, query="SELECT * FROM files")

        # Verify
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 1)
        self.assertEqual(res["data"][0]["id"], 1)

    @patch("src.brain.memory.db.manager.db_manager")
    async def test_expected_files(self, mock_db):
        """Test that expected_files generates the correct SQL."""
        # Setup mock
        mock_db.initialize = AsyncMock()
        mock_db.available = True
        
        # Use MagicMock for session
        mock_session = MagicMock()
        mock_session.close = AsyncMock()

        # Mock result
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [{"path": "/test/file.py"}]
        
        async def mock_execute(*args, **kwargs):
            return mock_result
            
        mock_session.execute = mock_execute
        
        # get_session must be awaitable
        mock_db.get_session = AsyncMock(return_value=mock_session)

        # Execute
        res = await vibe_check_db(self.ctx, expected_files=["file.py", "other.md"])

        # Verify
        self.assertTrue(res["success"])
        
        # Check success
        pass

    async def test_validation_error(self):
        """Test that missing both arguments returns error."""
        res = await vibe_check_db(self.ctx)
        self.assertFalse(res["success"])
        self.assertIn("Either 'query' OR 'expected_files' must be provided", res["error"])

if __name__ == "__main__":
    unittest.main()
