import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from middleware import MemoryMiddleware


def test_middleware():
    print("\n--- Testing Memory Middleware ---")
    middleware = MemoryMiddleware()

    # Test 1: Keyword Extraction
    print("\n[Test 1] Keyword Extraction")
    text = "What is the status of Project DeepAgents?"
    keywords = middleware._extract_keywords(text)
    print(f"Text: '{text}'")
    print(f"Keywords: {keywords}")
    if "DeepAgents" in keywords:
        print("✅ Keyword extraction passed")
    else:
        print("❌ Keyword extraction failed")

    # Test 2: Context Retrieval (Integration Test)
    print("\n[Test 2] Context Retrieval (Weaviate + Neo4j)")
    # We assume "DeepAgents" exists in both from previous tests
    query = "Tell me about DeepAgents"
    print(f"Querying context for: '{query}'")

    try:
        context = middleware.retrieve_context(query)
        print("\n--- Retrieved Context ---")
        print(context)
        print("-------------------------")

        if "DeepAgents" in context and (
            "Semantic Memory" in context or "Knowledge Graph" in context
        ):
            print("✅ Context retrieval passed")
        else:
            print("❌ Context retrieval failed (Missing expected content)")

    except Exception as e:
        print(f"❌ Context retrieval error: {e}")


if __name__ == "__main__":
    test_middleware()
