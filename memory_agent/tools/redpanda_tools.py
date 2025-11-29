import os
from langchain_core.tools import tool
from kafka import KafkaProducer, KafkaConsumer
import json

# Global Producer
producer = None


def get_producer():
    global producer
    if producer:
        return producer

    # Redpanda is Kafka compatible
    # Try to find a working broker
    brokers = os.environ.get("REDPANDA_CLUSTER_URLS", "localhost:18020").split(",")
    # Clean up URLs (remove kafka:// prefix if present)
    bootstrap_servers = []
    for b in brokers:
        b = b.replace("kafka://", "")
        bootstrap_servers.append(b)

    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        return producer
    except Exception as e:
        print(f"Failed to create Kafka producer: {e}")
        return None


@tool
def redpanda_produce(topic: str, message: str) -> str:
    """Produces a message to a Redpanda topic."""
    p = get_producer()
    if not p:
        return "Error: Could not connect to Redpanda cluster."

    try:
        # Send as a simple dict with 'content'
        future = p.send(topic, {"content": message})
        result = future.get(timeout=10)
        return f"Message sent to {topic} partition {result.partition} offset {result.offset}"
    except Exception as e:
        return f"Error producing message: {str(e)}"


@tool
def redpanda_consume(topic: str, timeout: int = 5) -> str:
    """Consumes messages from a Redpanda topic (reads last 5 messages)."""
    # This is a bit heavy for a tool, so we'll just read a few recent ones
    brokers = os.environ.get("REDPANDA_CLUSTER_URLS", "localhost:18020").split(",")
    bootstrap_servers = [b.replace("kafka://", "") for b in brokers]

    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",  # or latest
            enable_auto_commit=True,
            group_id="agent-tool-group",
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
            consumer_timeout_ms=timeout * 1000,
        )

        messages = []
        # Poll for a bit
        for msg in consumer:
            messages.append(msg.value)
            if len(messages) >= 5:
                break

        consumer.close()

        if not messages:
            return f"No messages found on {topic} (timeout {timeout}s)"
        return f"Read {len(messages)} messages: {messages}"

    except Exception as e:
        return f"Error consuming messages: {str(e)}"


def get_redpanda_tools():
    """Returns Redpanda tools."""
    return [redpanda_produce, redpanda_consume]
