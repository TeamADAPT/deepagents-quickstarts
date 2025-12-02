import os
import sys
import re
import time
import warnings
from typing import Optional

# --- NOVA TEMPLATE AGENT ---
# This is the standardized template for all "Nova" agents in the DeepAgents framework.
# It includes built-in support for:
# 1. Full Stack Memory (Redis Cache, Postgres Checkpointing, MongoDB Docs)
# 2. Episodic Memory (Reflection & Auto-Save)
# 3. Dynamic Configuration & Secret Management
# 4. LangSmith Observability

# Add checkpoint-postgres to path if needed (adjust path as necessary)
sys.path.insert(
    0, "/adapt/platform/novaops/frameworks/lang/langgraph/libs/checkpoint-postgres"
)

# Add current directory to sys.path to ensure local modules are found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import HumanMessage

# Import standard tools and modules
# Ensure these files exist in your agent's directory or are shared
from tools.admin_tools import check_reload_request
from session_manager import get_session_manager
from cache_tools import init_redis_cache
from team_structure import (
    build_team_graph,
)  # This is where your specific agent logic lives


def expand_vars(text: str) -> str:
    """Expands shell-style variables with defaults (e.g., ${VAR:-default})."""
    pattern = re.compile(r"\$\{([^}:]+)(?::-([^}]+))?\}")

    def replace(match):
        key = match.group(1)
        default = match.group(2)
        return os.environ.get(key, default if default is not None else "")

    return pattern.sub(replace, text)


def load_secrets():
    """Loads secrets from standard environment files."""
    secrets_files = ["/adapt/secrets/m2.env", "/adapt/secrets/db.env"]
    for path in secrets_files:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        if (value.startswith('"') and value.endswith('"')) or (
                            value.startswith("'") and value.endswith("'")
                        ):
                            value = value[1:-1]
                        if key not in os.environ:
                            os.environ[key] = value

    # Expand variables
    for key, value in os.environ.items():
        if "${" in value:
            os.environ[key] = expand_vars(value)

    # Map MiniMax keys to Anthropic (if using MiniMax)
    if "MiniMax_M2_CODE_PLAN_API_KEY" in os.environ:
        os.environ["ANTHROPIC_API_KEY"] = os.environ["MiniMax_M2_CODE_PLAN_API_KEY"]

    if "MiniMax_M2_GROUP_ID" in os.environ:
        os.environ["MINIMAX_GROUP_ID"] = os.environ["MiniMax_M2_GROUP_ID"]
    else:
        os.environ["MINIMAX_GROUP_ID"] = "123456"

    # Set LangSmith keys
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    if "LANGCHAIN_API_KEY" not in os.environ and "LANGSMITH_API_KEY" in os.environ:
        os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]

    # Set Project Name (Override this in your specific agent if needed)
    if "LANGCHAIN_PROJECT" not in os.environ:
        os.environ["LANGCHAIN_PROJECT"] = "Deep Agents Nova"


def get_postgres_connection_string() -> str:
    """Retrieves the Postgres connection string from env."""
    db_url = os.environ.get("POSTGRES_CLUSTER_URLS")
    if not db_url:
        # Fallback or error
        print("Warning: POSTGRES_CLUSTER_URLS not found, checking defaults...")
        return (
            "postgresql://postgres:postgres@localhost:5432/postgres"  # Default fallback
        )

    db_url = expand_vars(db_url)
    if "," in db_url:
        db_url = db_url.split(",")[0].strip()
    return db_url


def initialize_agent_graph(session_mgr, checkpointer):
    """Initializes the agent graph.

    Modify 'team_structure.py' to define your agent's logic.
    """
    print("Initializing Agent Team Graph...")
    return build_team_graph(checkpointer=checkpointer)


def main():
    # 1. Load Configuration
    load_secrets()

    # 2. Initialize Caching (Redis/DragonflyDB)
    try:
        init_redis_cache()
    except Exception as e:
        print(f"Warning: Redis Cache init failed: {e}")

    # 3. Initialize Session
    session_mgr = get_session_manager()
    session_id = session_mgr.get_session_id()
    print(f"Session ID: {session_id}")

    # 4. Setup Persistence (PostgreSQL)
    db_url = get_postgres_connection_string()

    # 5. Main Loop
    while True:
        try:
            with PostgresSaver.from_conn_string(db_url) as checkpointer:
                checkpointer.setup()

                # Build Agent
                agent = initialize_agent_graph(session_mgr, checkpointer)

                # Config
                config = {
                    "configurable": {"thread_id": session_id},
                    "recursion_limit": 100,  # Adjust as needed
                }

                print(f"Nova Agent Ready. Session: {session_id}")
                print("Type 'quit' to exit.")

                # Interaction Loop
                while True:
                    if check_reload_request():
                        print("\n[System] Reloading Configuration...")
                        break

                    user_input = input("User: ")
                    if user_input.lower() in ["quit", "exit"]:
                        return

                    inputs = {"messages": [HumanMessage(content=user_input)]}

                    # Stream Output
                    for event in agent.stream(inputs, config=config):
                        for key, value in event.items():
                            # Customize output handling here
                            if "messages" in value and value["messages"]:
                                last_msg = value["messages"][-1]
                                content = last_msg.content
                                agent_name = key

                                # Handle list content
                                if isinstance(content, list):
                                    for item in content:
                                        if (
                                            isinstance(item, dict)
                                            and item.get("type") == "text"
                                        ):
                                            print(f"[{agent_name}]: {item.get('text')}")
                                else:
                                    print(f"[{agent_name}]: {content}")

                                # Print Tool Calls
                                if (
                                    hasattr(last_msg, "tool_calls")
                                    and last_msg.tool_calls
                                ):
                                    for tool_call in last_msg.tool_calls:
                                        print(f"  [Tool Call: {tool_call['name']}]")

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Critical Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
