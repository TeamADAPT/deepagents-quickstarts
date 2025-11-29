import os
from langchain.globals import set_llm_cache
from langchain_community.cache import RedisCache
from redis import Redis


def init_redis_cache():
    """Initialize Redis caching for LLM responses."""
    redis_url = os.environ.get("DRAGONFLY_NODE_1_URL")
    if not redis_url:
        # Fallback to constructing from parts if full URL not set
        password = os.environ.get(
            "DRAGONFLY_PASSWORD", "df_cluster_2024_adapt_research"
        )
        port = os.environ.get("DRAGONFLY_NODE_1_PORT", "18000")
        redis_url = f"redis://:{password}@localhost:{port}"

    print(f"Initializing Redis Cache at {redis_url.split('@')[-1]}...")

    try:
        redis_client = Redis.from_url(redis_url)
        set_llm_cache(RedisCache(redis_=redis_client))
        print("✅ Redis Cache initialized successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize Redis Cache: {e}")
