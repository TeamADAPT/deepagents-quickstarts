import os
import sys
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_tools import init_memory_collection, save_memory, recall_memory
from tools.graph_tools import add_graph_node, add_graph_edge, query_graph


def test_weaviate():
    print("\n--- Testing Weaviate Integration ---")
    try:
        print("Initializing collection...")
        init_memory_collection()

        print("Saving memory...")
        res = save_memory.invoke("The project 'DeepAgents' uses Weaviate for memory.")
        print(res)

        print("Recalling memory...")
        # Allow some time for indexing if needed (though usually near-instant for small data)
        time.sleep(1)
        res = recall_memory.invoke("What does DeepAgents use?")
        print(f"Result: {res}")

        if "Weaviate" in res:
            print("✅ Weaviate Test Passed")
        else:
            print("❌ Weaviate Test Failed")

    except Exception as e:
        print(f"❌ Weaviate Test Error: {e}")


def test_neo4j():
    print("\n--- Testing Neo4j Integration ---")
    try:
        print("Adding nodes...")
        print(
            add_graph_node.invoke(
                {
                    "label": "Project",
                    "name": "DeepAgents",
                    "properties": '{"status": "active"}',
                }
            )
        )
        print(
            add_graph_node.invoke(
                {
                    "label": "Database",
                    "name": "Weaviate",
                    "properties": '{"type": "vector"}',
                }
            )
        )

        print("Adding edge...")
        print(
            add_graph_edge.invoke(
                {"from_name": "DeepAgents", "relation": "USES", "to_name": "Weaviate"}
            )
        )

        print("Querying graph...")
        res = query_graph.invoke(
            "MATCH (p:Project)-[:USES]->(d:Database) RETURN p.name, d.name"
        )
        print(f"Result: {res}")

        if "DeepAgents" in res and "Weaviate" in res:
            print("✅ Neo4j Test Passed")
        else:
            print("❌ Neo4j Test Failed")

    except Exception as e:
        print(f"❌ Neo4j Test Error: {e}")


if __name__ == "__main__":
    # Ensure env vars are loaded (mocking what agent.py does or relying on system env)
    # For this test, we assume the environment is set up or defaults work.
    test_weaviate()
    test_neo4j()
