import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from src.brain.memory.db.manager import db_manager
from src.brain.memory.knowledge_graph import knowledge_graph
from src.brain.memory.memory import long_term_memory


async def smoke_test():

    # 1. Initialize DB
    await db_manager.initialize()
    if not db_manager.available:
        return

    # 2. Check ChromaDB
    if not long_term_memory.available:
        return

    # 3. Add node to Graph (this should sync to Vector)
    node_id = "test:smoke_test_node"
    success = await knowledge_graph.add_node(
        node_type="CONCEPT",
        node_id=node_id,
        attributes={
            "description": "This is a test node for semantic verification",
            "content": "Complex data about agent interaction and context improvement.",
        },
    )

    if success:
        # 4. Verify in ChromaDB
        results = long_term_memory.knowledge.query(query_texts=["agent interaction"], n_results=1)

        distances = results.get("distances") if results else None
        if (
            results
            and results.get("ids")
            and distances
            and results["ids"]
            and node_id in results["ids"][0]
            and len(distances) > 0
            and len(distances[0]) > 0
        ):
            distances[0][0]

            # 5. Add Edge
            target_id = "test:target_node"
            await knowledge_graph.add_node("CONCEPT", target_id, {"description": "Target"})
            edge_success = await knowledge_graph.add_edge(node_id, target_id, "TESTS")
            if edge_success:
                pass
        else:
            pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(smoke_test())
