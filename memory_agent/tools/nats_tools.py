import asyncio
import os
from langchain_core.tools import tool
import nats
from nats.errors import ConnectionClosedError, TimeoutError, NoServersError

# Global NATS connection (simplified for this context)
nc = None


async def get_nats_connection():
    global nc
    if nc and not nc.is_closed:
        return nc

    nats_url = os.environ.get("NATS_URL", "nats://localhost:4222")
    user = os.environ.get("NATS_USER")
    password = os.environ.get("NATS_PASSWORD")

    print(f"[NATS] Connecting to {nats_url}...")

    try:
        # Explicitly pass user/pass if available, regardless of URL
        # nats-py prefers explicit args over URL info usually
        nc = await nats.connect(
            servers=[nats_url], user=user, password=password, connect_timeout=5
        )
    except Exception as e:
        print(f"[NATS] Connection failed: {e}")
        raise e

    return nc


@tool
def nats_publish(subject: str, message: str) -> str:
    """Publishes a message to a NATS subject."""

    async def _publish():
        try:
            nc = await get_nats_connection()
            await nc.publish(subject, message.encode())
            return f"Published to {subject}"
        except Exception as e:
            return f"Error publishing: {str(e)}"

    # Run async in sync context
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_publish())
    except Exception as e:
        return f"System Error in nats_publish: {e}"


@tool
def nats_subscribe(subject: str, timeout: int = 5) -> str:
    """Subscribes to a NATS subject and waits for a message (blocking)."""

    async def _subscribe():
        try:
            nc = await get_nats_connection()
            sub = await nc.subscribe(subject)
            try:
                msg = await sub.next_msg(timeout=timeout)
                return f"Received on {subject}: {msg.data.decode()}"
            except TimeoutError:
                return f"No message received on {subject} within {timeout}s"
            finally:
                await sub.unsubscribe()
        except Exception as e:
            return f"Error subscribing: {str(e)}"

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_subscribe())
    except Exception as e:
        return f"System Error in nats_subscribe: {e}"


def get_nats_tools():
    """Returns NATS tools."""
    return [nats_publish, nats_subscribe]
