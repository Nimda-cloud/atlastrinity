import asyncio
import os
import sys

sys.path.append(os.getcwd())

from src.brain.db.manager import db_manager
from src.brain.knowledge_graph import knowledge_graph
from src.brain.memory import long_term_memory


async def smoke_test():
    print("--- Memory & Graph Smoke Test ---")

    # 1. Initialize DB
    await db_manager.initialize()
    if not db_manager.available:
        print("❌ DB NOT available")
        return
    print("✅ DB initialized")

    # 2. Check ChromaDB
    if not long_term_memory.available:
        print("❌ ChromaDB NOT available")
        return
    print(f"✅ ChromaDB available (Path: {long_term_memory.get_stats().get('path')})")

    # 3. Add node to Graph (this should sync to Vector)
    node_id = "test:smoke_test_node"
    print(f"Adding node: {node_id}")
    success = await knowledge_graph.add_node(
        node_type="CONCEPT",
        node_id=node_id,
        attributes={
            "description": "This is a test node for semantic verification",
            "content": "Complex data about agent interaction and context improvement.",
        },
    )

    if success:
        print("✅ Node added to PostgreSQL Graph")

        # 4. Verify in ChromaDB
        print("Searching for node in ChromaDB...")
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
            dist = distances[0][0]
            print(f"✅ Node FOUND in ChromaDB vectors! (Distance: {dist:.4f})")

            # 5. Add Edge
            target_id = "test:target_node"
            await knowledge_graph.add_node("CONCEPT", target_id, {"description": "Target"})
            edge_success = await knowledge_graph.add_edge(node_id, target_id, "TESTS")
            if edge_success:
                print("✅ Edge added successfully")
        else:
            print("❌ Node NOT found in ChromaDB")
    else:
        print("❌ Failed to add node to Graph")


if __name__ == "__main__":
    asyncio.run(smoke_test())
