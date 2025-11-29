import os
import sys
import re
import warnings

# Only add checkpoint-postgres to path, use installed versions for others
sys.path.insert(
    0, "/adapt/platform/novaops/frameworks/lang/langgraph/libs/checkpoint-postgres"
)

# Add current directory to sys.path to ensure local modules are found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.postgres import PostgresSaver

# Import new tools
from tools.admin_tools import check_reload_request
from session_manager import get_session_manager


def expand_vars(text):
    """Expands shell-style variables with defaults."""
    pattern = re.compile(r"\$\{([^}:]+)(?::-([^}]+))?\}")

    def replace(match):
        key = match.group(1)
        default = match.group(2)
        return os.environ.get(key, default if default is not None else "")

    return pattern.sub(replace, text)


def load_secrets():
    """Loads secrets from env files if not already present."""
    secrets_files = ["/adapt/secrets/m2.env", "/adapt/secrets/db.env"]
    for path in secrets_files:
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove surrounding quotes if present
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

    # Map MiniMax keys
    if "MiniMax_M2_CODE_PLAN_API_KEY" in os.environ:
        os.environ["ANTHROPIC_API_KEY"] = os.environ["MiniMax_M2_CODE_PLAN_API_KEY"]

    if "MiniMax_M2_GROUP_ID" in os.environ:
        os.environ["MINIMAX_GROUP_ID"] = os.environ["MiniMax_M2_GROUP_ID"]
    else:
        # Set a dummy group ID if not present, as some versions might require it but not use it for chat
        os.environ["MINIMAX_GROUP_ID"] = "123456"

    # Set LangSmith keys (Standard LangChain naming)
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    if "LANGCHAIN_API_KEY" not in os.environ and "LANGSMITH_API_KEY" in os.environ:
        os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]

    os.environ["LANGCHAIN_PROJECT"] = "Deep Agents Memory"


def get_postgres_connection_string():
    """Retrieves the Postgres connection string."""
    db_url = os.environ.get("POSTGRES_CLUSTER_URLS")
    if not db_url:
        raise ValueError("POSTGRES_CLUSTER_URLS not found")

    # Expand again just in case
    db_url = expand_vars(db_url)

    if "," in db_url:
        db_url = db_url.split(",")[0].strip()
    return db_url


from team_structure import build_team_graph


def initialize_agent_graph(session_mgr, checkpointer):
    """Initializes the agent graph and tools."""
    print("Initializing Agent Team Graph...")

    # Build the team graph with persistence
    agent = build_team_graph(checkpointer=checkpointer)

    return agent


def main():
    load_secrets()
    # init_db()

    # Initialize Session Manager
    session_mgr = get_session_manager()
    print(f"Session ID: {session_mgr.get_session_id()}")

    # DB URL for checkpointer
    db_url = get_postgres_connection_string()

    # SYSTEM LOOP (Handles Reloads)
    while True:
        try:
            # Initialize Checkpointer Context
            with PostgresSaver.from_conn_string(db_url) as checkpointer:
                checkpointer.setup()

                # Initialize Agent
                agent = initialize_agent_graph(session_mgr, checkpointer)

                # Use the session ID from the manager as the thread ID for persistence
                thread_id = session_mgr.get_session_id()
                config = {
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": 2000000,
                }

                print(f"Deep Agent ready with Enterprise Tools. Session: {thread_id}")
                print("Type 'quit' to exit.")

                # INTERACTION LOOP
                while True:
                    # Check for reload request
                    if check_reload_request():
                        print("\n[System] Reloading Agent Configuration...")
                        break  # Break inner loop to re-initialize

                    user_input = input("User: ")
                    if user_input.lower() in ["quit", "exit"]:
                        return  # Exit program

                    # Run the agent
                    from langchain_core.messages import HumanMessage

                    inputs = {"messages": [HumanMessage(content=user_input)]}

                    # Stream the output
                    for event in agent.stream(inputs, config=config):
                        for key, value in event.items():
                            if key == "agent" or key in [
                                "Planner",
                                "Coder",
                                "Reviewer",
                            ]:
                                if "messages" in value and value["messages"]:
                                    last_msg = value["messages"][-1]
                                    content = last_msg.content
                                    agent_name = key if key != "agent" else "Agent"
                                    # Handle MiniMax list-of-dicts content
                                    if isinstance(content, list):
                                        for item in content:
                                            if isinstance(item, dict):
                                                if item.get("type") == "text":
                                                    print(
                                                        f"[{agent_name}]: {item.get('text')}"
                                                    )
                                                elif item.get("type") == "thinking":
                                                    pass
                                    else:
                                        print(f"[{agent_name}]: {content}")

                                    if (
                                        hasattr(last_msg, "tool_calls")
                                        and last_msg.tool_calls
                                    ):
                                        for tool_call in last_msg.tool_calls:
                                            print(
                                                f"  [Calling Tool: {tool_call['name']} with {tool_call['args']}]"
                                            )
                            elif key == "tools":
                                print("Tool execution completed.")
                                if "messages" in value and value["messages"]:
                                    for msg in value["messages"]:
                                        print(f"  [Tool Output]: {msg.content}")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Critical System Error: {e}")
            # Optional: wait before retrying to avoid tight loops on error
            import time

            time.sleep(5)


if __name__ == "__main__":
    main()
