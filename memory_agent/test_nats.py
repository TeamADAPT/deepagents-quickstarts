#!/usr/bin/env python3
import os
import asyncio
try:
    import nats
except ImportError:
    print("nats library not installed")
    import subprocess
    subprocess.check_call(['pip', 'install', 'nats-py'])
    import nats

async def test_nats():
    try:
        # Connect to NATS
        nats_url = os.getenv('NATS_URL', 'nats://localhost:4222')
        print(f"Connecting to NATS at: {nats_url}")
        
        nc = await nats.connect(nats_url)
        print("Connected to NATS successfully!")
        
        # Publish message
        await nc.publish("test.subject", b"Hello NATS")
        print("Published 'Hello NATS' to test.subject")
        
        # Subscribe to the same subject
        async def message_handler(msg):
            print(f"Received: {msg.data.decode()}")
        
        sub = await nc.subscribe("test.subject", cb=message_handler)
        print("Subscribed to test.subject")
        
        # Wait a moment for the message
        await asyncio.sleep(1)
        
        # Close
        await sub.drain()
        await nc.drain()
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_nats())
