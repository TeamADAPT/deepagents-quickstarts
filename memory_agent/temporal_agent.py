import asyncio
import os
import sys
import logging
from datetime import timedelta
from typing import List, Dict, Any

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

# Import existing agent components
# We need to add the current directory to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from session_manager import SessionManager

# Configure Logfire (Observability)
try:
    import logfire

    logfire.configure(
        send_to_logfire=False
    )  # Use local Jaeger if available, or just console
    logfire.instrument_pydantic_ai()  # If we use Pydantic AI later
except ImportError:
    pass

# Setup logging
logging.basicConfig(level=logging.INFO)

# --- Temporal Activity ---


@activity.defn
async def run_agent_turn_activity(user_input: str, thread_id: str) -> str:
    """
    Executes one turn of the LangGraph agent.
    This is the "Durable" part. If this crashes, Temporal retries it.
    """
    # Imports moved here to avoid Temporal Sandbox violations
    from team_structure import build_team_graph
    from langchain_core.messages import HumanMessage
    from langgraph.checkpoint.postgres import PostgresSaver
    from psycopg_pool import ConnectionPool

    print(f"\n[Activity] 🤖 Processing turn for thread {thread_id}...")

    # Load Secrets (Same as agent.py)
    try:
        from dotenv import load_dotenv

        load_dotenv("/adapt/secrets/m2.env")
    except Exception as e:
        print(f"Warning: Could not load secrets: {e}")

    # Database Setup (Same as agent.py)
    DB_URI = os.environ.get("POSTGRES_CLUSTER_URLS")
    if not DB_URI:
        return "Error: POSTGRES_CLUSTER_URLS not set."

    pool = ConnectionPool(conninfo=DB_URI, max_size=20, kwargs={"autocommit": True})
    checkpointer = PostgresSaver(pool)
    checkpointer.setup()

    # Build Graph
    agent_graph = build_team_graph(checkpointer=checkpointer)

    # Config
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,  # Lower limit for individual turns to avoid infinite loops
    }

    # Run Agent
    # We collect all output to return it.
    # In a real app, we might push updates to a queue or webhook.
    final_response = ""

    inputs = {
        "messages": [HumanMessage(content=user_input)],
        "team_members": ["Planner", "Coder", "Reviewer"],
    }

    # We use invoke instead of stream to get the final state,
    # OR we can iterate stream to capture intermediate logs.
    # Let's iterate stream to show progress in the worker logs.

    try:
        for event in agent_graph.stream(inputs, config=config):
            for key, value in event.items():
                # Format output similar to agent.py
                agent_name = key
                if key == "agent":
                    agent_name = "Agent"

                if "messages" in value:
                    last_msg = value["messages"][-1]
                    content = last_msg.content
                    log_msg = f"[{agent_name}]: {content[:100]}..."
                    print(log_msg)

                    # Accumulate response if it's from a relevant agent
                    # For simplicity, we'll return the last message content as the "response"
                    final_response = content
                elif "next_agent" in value:
                    print(f"[{agent_name}] -> {value['next_agent']}")
    except Exception as e:
        print(f"[Activity] Error: {e}")
        raise e  # Let Temporal handle retry

    return final_response


# --- Temporal Workflow ---


@workflow.defn
class DeepAgentTurnWorkflow:
    @workflow.run
    async def run(self, user_input: str, thread_id: str) -> str:
        # Execute the activity
        # Retry policy: Retry up to 3 times, then fail (to avoid infinite loops on bad code)
        return await workflow.execute_activity(
            run_agent_turn_activity,
            args=[user_input, thread_id],
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3),
        )


# --- Main Execution ---


async def main():
    # 1. Start Temporal Worker (in the background of this script for simplicity)
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="deep-agent-queue",
        workflows=[DeepAgentTurnWorkflow],
        activities=[run_agent_turn_activity],
    )

    # Run worker in background task
    worker_task = asyncio.create_task(worker.run())
    print("✅ Temporal Worker Started on 'deep-agent-queue'")

    # 2. Session Setup
    session_manager = SessionManager()
    thread_id = session_manager.get_session_id()
    print(f"🧵 Session ID: {thread_id}")
    print("💬 Deep Agent (Temporal Powered) Ready! Type 'quit' to exit.")

    # 3. Chat Loop
    while True:
        try:
            user_input = await asyncio.to_thread(input, "\nUser: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                break

            print("⏳ Sending to Temporal Cloud...")

            # Execute Workflow
            result = await client.execute_workflow(
                DeepAgentTurnWorkflow.run,
                args=[user_input, thread_id],
                id=f"turn-{thread_id}-{os.urandom(4).hex()}",
                task_queue="deep-agent-queue",
            )

            print(f"\n🤖 Agent: {result}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    # Cleanup
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    print("👋 Bye!")


if __name__ == "__main__":
    asyncio.run(main())
