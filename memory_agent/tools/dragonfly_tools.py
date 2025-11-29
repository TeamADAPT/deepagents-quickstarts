import os
import redis
from langchain_core.tools import tool

# Global Redis/Dragonfly client
r = None


def get_redis_client():
    global r
    if r:
        return r

    # Parse Dragonfly URL or construct from parts
    # db.env has DRAGONFLY_NODE_1_URL etc.
    # We'll try a simple connection first.
    url = os.environ.get("DRAGONFLY_NODE_1_URL") or os.environ.get(
        "REDIS_URL", "redis://localhost:6379"
    )

    r = redis.from_url(url, decode_responses=True)
    return r


@tool
def kv_set(key: str, value: str) -> str:
    """Sets a key-value pair in the shared store (DragonflyDB)."""
    try:
        client = get_redis_client()
        client.set(key, value)
        return f"Set {key} successfully"
    except Exception as e:
        return f"Error setting key: {str(e)}"


@tool
def kv_get(key: str) -> str:
    """Gets a value from the shared store (DragonflyDB)."""
    try:
        client = get_redis_client()
        val = client.get(key)
        return str(val) if val is not None else "Key not found"
    except Exception as e:
        return f"Error getting key: {str(e)}"


@tool
def kv_list_keys(pattern: str = "*") -> str:
    """Lists keys matching a pattern."""
    try:
        client = get_redis_client()
        keys = client.keys(pattern)
        return str(keys)
    except Exception as e:
        return f"Error listing keys: {str(e)}"


def get_dragonfly_tools():
    """Returns DragonflyDB tools."""
    return [kv_set, kv_get, kv_list_keys]
