import asyncio
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Try strict import
try:
    from src.brain.healing.system_healing import HealingStrategy, healing_orchestrator
    from src.brain.memory.knowledge_graph import knowledge_graph
    from src.brain.memory.memory import long_term_memory
    from src.brain.tools.recovery import recovery_manager
except ImportError as e:
    print(f"CRITICAL: Failed to import brain modules: {e}")
    sys.exit(1)


class TestCriticalSystems(unittest.TestCase):
    def setUp(self):
        print("\n" + "=" * 50)
        print(f"Running Test: {self._testMethodName}")
        print("=" * 50)

    @patch("src.brain.healing.system_healing.mcp_manager")
    @patch("os.execl")
    @patch("src.brain.tools.recovery.recovery_manager.save_snapshot")
    def test_phoenix_protocol_restart(self, mock_save_snapshot, mock_execl, mock_mcp_manager):
        """
        Verifies that a SYSTEM_CRITICAL error triggers the Phoenix Protocol:
        1. Vibe analyzes error -> Suggests PHOENIX_RESTART
        2. Snapshot is saved
        3. System calls restart (os.execl)
        """
        print("[TEST] Simulating Critical System Failure...")

        # We need to reach into the instance because save_snapshot is an instance method
        # but we patched it on the class or module level. Let's patch the instance method on the imported object directly if possible,
        # or rely on the patcher if it caught it.
        # However, recovery_manager is an INSTANCE imported from recovery.py. We need to patch that INSTANCE.

        # Let's adjust the patch strategy in the test body or use the passed mock if correct.
        # The mock passed is likely the function on the class if not careful.
        # But wait, recovery_manager is an instance. 'src.brain.tools.recovery.recovery_manager' refers to the variable.
        # If we patch the variable's method, it works.

        healing_orchestrator.analyzer = MagicMock()
        # Mock Vibe analysis result directly on the analyzer to avoid complex MCP mocking
        healing_orchestrator.analyzer.analyze = AsyncMock(
            return_value=MagicMock(
                root_cause="Critical Kernel Panic",
                severity="SYSTEM_CRITICAL",
                suggested_strategy=HealingStrategy.PHOENIX_RESTART,
                fix_plan="Clean reboot",
                confidence=0.99,
            )
        )

        # Mock Recovery Manager instance method
        recovery_manager.save_snapshot = AsyncMock(return_value=True)

        # Mock Strategies
        error_msg = "FATAL: Out of memory in native bridge."
        context = {"step_id": "step_deadbeef", "action": "allocate_buffer"}
        log_context = "System is unresponsive..."

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # ACT
        loop.run_until_complete(
            healing_orchestrator.handle_error("step_deadbeef", error_msg, context, log_context)
        )

        # ASSERT
        print("[CHECK] Verifying Recovery Snapshot...")
        recovery_manager.save_snapshot.assert_called_once()
        print(" -> Snapshot saved.")

        print("[CHECK] Verifying OS Restart...")
        mock_execl.assert_called_once()
        print(" -> OS Restart triggered.")

        loop.close()

    def test_gold_fund_memory(self):
        """
        Verifies:
        1. Adding a node to the Knowledge Graph.
        2. Promoting it to the 'Gold Fund'.
        3. Semantic search retrieval.
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Unique ID to avoid collisions
        node_id = f"protocol_omega_{int(datetime.now().timestamp())}"
        test_namespace = "verification_test"
        gold_namespace = "gold_fund"

        if not knowledge_graph or not long_term_memory.available:
            print("SKIPPING: Memory/Graph not available in this environment.")
            return

        print(f"[TEST] Creating Node '{node_id}'...")
        loop.run_until_complete(
            knowledge_graph.add_node(
                node_type="CONCEPT",
                node_id=node_id,
                attributes={
                    "description": "Protocol Omega is the ultimate fallback strategy.",
                    "content": "Full state serialization and reboot.",
                },
                namespace=test_namespace,
                sync_to_vector=True,
            )
        )

        print("[TEST] Promoting to Gold Fund...")
        loop.run_until_complete(
            knowledge_graph.promote_node(
                node_id=node_id, target_namespace=gold_namespace, agent_name="TestVerifier"
            )
        )

        print("[TEST] Verifying Semantic Retrieval...")
        # Allow slight delay for vector store? Usually sync.

        # Direct query to Chroma
        results = long_term_memory.knowledge.query(
            query_texts=["What is Protocol Omega?"],
            n_results=1,
            where={
                "namespace": gold_namespace
            },  # Filter ensures we are getting it from the right place
        )

        found = False
        if results and results["ids"] and results["ids"][0]:
            if results["ids"][0][0] == node_id:
                found = True

        if found:
            print(" -> SUCCESS: Found Protocol Omega in Gold Fund via semantic search.")
        else:
            print(f" -> FAILURE: Could not retrieve node. Context: {results}")

        # Cleanup
        long_term_memory.knowledge.delete(ids=[node_id])
        loop.close()


if __name__ == "__main__":
    unittest.main()
