import sys
import os
import time
from langchain_core.messages import HumanMessage, AIMessage

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reflection import reflect_on_conversation
from memory_tools import recall_memory
from tools.graph_tools import query_graph
from agent import load_secrets


def test_episodic_memory():
    load_secrets()  # Load environment variables
    print("\n--- Testing Episodic Memory (Reflection) ---")

    # 1. Simulate a conversation state
    print("\n[Test 1] Simulating Conversation")
    mock_state = {
        "messages": [
            HumanMessage(
                content="I want to build a new Python web scraper called 'SpiderBot'."
            ),
            AIMessage(
                content="I can help with that. We should use BeautifulSoup and requests."
            ),
            HumanMessage(
                content="Great. It needs to depend on the 'requests' library."
            ),
            AIMessage(content="Noted. I'll add that dependency."),
        ]
    }

    # 2. Run Reflection
    print("Running reflection...")
    try:
        result = reflect_on_conversation(mock_state)
        print(f"Reflection Result: {result}")
    except Exception as e:
        print(f"❌ Reflection Failed: {e}")
        return

    # 3. Verify Semantic Memory (Weaviate)
    print("\n[Test 2] Verifying Semantic Memory")
    time.sleep(2)  # Allow for indexing
    memories = recall_memory.invoke({"query": "SpiderBot"})
    print(f"Recalled Memories:\n{memories}")

    if "SpiderBot" in memories:
        print("✅ Semantic Memory Updated")
    else:
        print("❌ Semantic Memory Verification Failed")

    # 4. Verify Knowledge Graph (Neo4j)
    print("\n[Test 3] Verifying Knowledge Graph")
    # Check for Project node
    graph_res = query_graph.invoke({"cypher": "MATCH (n {name: 'SpiderBot'}) RETURN n"})
    print(f"Graph Node Check: {graph_res}")

    if "SpiderBot" in str(graph_res):
        print("✅ Knowledge Graph Node Created")
    else:
        print("❌ Knowledge Graph Verification Failed")


if __name__ == "__main__":
    test_episodic_memory()
