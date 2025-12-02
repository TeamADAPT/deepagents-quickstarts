import os
import weaviate
import weaviate.classes as wvc
from langchain_core.tools import tool


def get_weaviate_client():
    """Establishes a connection to the Weaviate vector database."""
    # Load secrets manually if not already in env
    weaviate_url = os.environ.get("WEAVIATE_URL")
    if not weaviate_url:
        # Fallback to reading the file directly if env var not set
        try:
            with open("/adapt/secrets/db.env") as f:
                for line in f:
                    if line.startswith("WEAVIATE_URL="):
                        weaviate_url = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception as e:
            print(f"Error reading db.env: {e}")

    if not weaviate_url or "${" in weaviate_url:
        # Default to localhost port 18050 if not found or if it contains unexpanded variables
        # In a real scenario we'd implement full env expansion, but for this quickstart 18050 is the known port.
        weaviate_url = "http://localhost:18050"

    # Connect to Weaviate
    try:
        port_str = weaviate_url.split(":")[-1]
        # Remove any trailing path if present (though unlikely for base URL)
        if "/" in port_str:
            port_str = port_str.split("/")[0]

        client = weaviate.connect_to_local(
            port=int(port_str),
            grpc_port=18051,  # Default gRPC port
            skip_init_checks=True,
        )
        return client
    except Exception as e:
        print(f"Failed to connect to Weaviate: {e}")
        raise


def init_db():
    """Initializes the Weaviate collection for memories."""
    client = get_weaviate_client()
    try:
        if not client.collections.exists("AgentMemory"):
            client.collections.create(
                name="AgentMemory",
                vectorizer_config=wvc.config.Configure.Vectorizer.none(),  # We'll use raw text or external embeddings if needed, but for now let's assume simple text search or we need to configure a module.
                # Actually, without a vectorizer module configured in Weaviate, we might need to provide vectors or use a default.
                # Let's check if we can use a default text2vec-transformers or similar if available, otherwise we might need to rely on keyword search or provide vectors.
                # For this quickstart, let's assume the Weaviate instance might have a default vectorizer or we use simple keyword search if not.
                # BUT the goal is "Deep Memory".
                # If the local Weaviate doesn't have a vectorizer module enabled, we might need to use LangChain's Embeddings to generate vectors and push them.
                # To keep it simple and dependency-light, let's try to use Weaviate's default if available, or just store text.
                # Wait, the user wants "engines we have". Weaviate is running.
                properties=[
                    wvc.config.Property(
                        name="content", data_type=wvc.config.DataType.TEXT
                    ),
                    wvc.config.Property(
                        name="timestamp", data_type=wvc.config.DataType.DATE
                    ),
                ],
            )
            print("Created AgentMemory collection in Weaviate.")
    finally:
        client.close()


@tool
def save_memory(content: str) -> str:
    """Saves a piece of information to long-term memory using Weaviate.

    Use this tool to remember important facts, user preferences, or context
    that should be preserved across different sessions.

    Args:
        content: The text content to remember.
    """
    client = get_weaviate_client()
    try:
        collection = client.collections.get("AgentMemory")
        import datetime

        # Generate embedding using sentence-transformers
        vector = None
        try:
            from sentence_transformers import SentenceTransformer

            # Use a small, fast model. 'all-MiniLM-L6-v2' is standard but might need download.
            # We'll try to load it, if it fails we fall back to no vector.
            model = SentenceTransformer("all-MiniLM-L6-v2")
            vector = model.encode(content).tolist()
        except Exception as e:
            print(f"Embedding generation failed (falling back to keyword only): {e}")

        collection.data.insert(
            properties={
                "content": content,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            vector=vector,
        )
        return f"Successfully saved to Weaviate memory: {content}"
    except Exception as e:
        return f"Failed to save memory: {e}"
    finally:
        client.close()


@tool
def recall_memory(query: str) -> str:
    """Recalls information from long-term memory based on semantic or keyword search.

    Use this tool to retrieve past information, user preferences, or context.

    Args:
        query: The keyword or phrase to search for.
    """
    # Use direct REST/GraphQL call to avoid gRPC issues with the client
    import requests

    weaviate_url = os.environ.get("WEAVIATE_URL")
    if not weaviate_url or "${" in weaviate_url:
        weaviate_url = "http://localhost:18050"

    # GraphQL query for BM25 search
    gql_query = """
    {
      Get {
        AgentMemory(
          limit: 5
          bm25: {
            query: "%s"
            properties: ["content"]
          }
        ) {
          content
          timestamp
        }
      }
    }
    """ % query.replace('"', '\\"')  # Simple escaping

    try:
        response = requests.post(
            f"{weaviate_url}/v1/graphql",
            json={"query": gql_query},
            headers={"Content-Type": "application/json"},
        )

        if response.status_code != 200:
            return f"Error querying Weaviate: {response.text}"

        data = response.json()
        if "errors" in data:
            return f"GraphQL Error: {data['errors']}"

        memories = data.get("data", {}).get("Get", {}).get("AgentMemory", [])

        if not memories:
            return "No relevant memories found."

        results = []
        for mem in memories:
            content = mem.get("content")
            timestamp = mem.get("timestamp", "Unknown time")
            results.append(f"[{timestamp}] {content}")

        return "\n".join(results)
    except Exception as e:
        return f"Failed to recall memory: {e}"
