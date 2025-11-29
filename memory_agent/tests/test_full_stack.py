import sys
import os
import time

# Add current directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cache_tools import init_redis_cache
from tools.mongo_tools import save_document, read_document
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage


def test_full_stack():
    print("\n--- Testing Full Stack Memory ---")

    # 1. Test Redis Cache
    print("\n[Test 1] Redis Caching")
    try:
        init_redis_cache()
        # We can't easily test the cache hit without an LLM call, but initialization success is a good start.
        # We could try to access the redis client directly if we exposed it, but for now we rely on the print output.
    except Exception as e:
        print(f"❌ Redis Cache Error: {e}")

    # 2. Test MongoDB Tools
    print("\n[Test 2] MongoDB Document Store")
    try:
        # Check connection first with short timeout
        from pymongo import MongoClient

        client = MongoClient(
            os.environ.get("MONGODB_URL", "mongodb://localhost:18070"),
            serverSelectionTimeoutMS=2000,
        )
        client.server_info()  # Trigger connection

        doc_title = f"Test Doc {int(time.time())}"
        print(f"Saving document: {doc_title}")
        res = save_document.invoke(
            {
                "title": doc_title,
                "content": "This is a test document content.",
                "tags": ["test", "memory"],
            }
        )
        print(f"Save Result: {res}")

        print("Reading document...")
        read_res = read_document.invoke({"query": doc_title})
        print(f"Read Result:\n{read_res}")

        if doc_title in read_res:
            print("✅ MongoDB Test Passed")
        else:
            print("❌ MongoDB Test Failed (Document not found)")
    except Exception as e:
        print(f"⚠️ MongoDB Service not available (Skipping): {e}")

    # 3. Test PostgreSQL Checkpointing
    print("\n[Test 3] PostgreSQL Checkpointing")
    db_url = os.environ.get(
        "POSTGRES_CLUSTER_URLS",
        "postgresql://postgres_admin_user:changeme@localhost:18030/teamadapt",
    )
    if "," in db_url:
        db_url = db_url.split(",")[0].strip()

    try:
        with PostgresSaver.from_conn_string(db_url) as checkpointer:
            checkpointer.setup()
            print("✅ PostgresSaver initialized and setup successfully.")

            # Basic write/read test
            config = {
                "configurable": {"thread_id": "test_thread_1", "checkpoint_ns": ""}
            }
            checkpoint = {
                "v": 1,
                "ts": "2024-01-01T00:00:00.000000+00:00",
                "id": "test_checkpoint_id",
                "channel_values": {},
                "channel_versions": {},
                "versions_seen": {},
                "pending_sends": [],
            }
            checkpointer.put(config, checkpoint, {}, {})
            checkpoint = checkpointer.get(config)
            if checkpoint:
                print("✅ Checkpoint saved and retrieved.")
            else:
                print("❌ Checkpoint retrieval failed.")

    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"❌ PostgreSQL Error: {e}")


if __name__ == "__main__":
    test_full_stack()
