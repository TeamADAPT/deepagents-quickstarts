import os
import sys
import re
import warnings
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from memory_tools import save_memory, recall_memory, init_db
from team_structure import build_team_graph
from session_manager import get_session_manager
# import psycopg2

# Suppress LangGraph deprecation warning
warnings.filterwarnings("ignore", message=".*create_react_agent has been moved.*")

# Add current directory to sys.path to ensure local modules are found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def expand_vars(text):
    """Expands shell-style variables with defaults."""
    pattern = re.compile(r"\$\{([^}:]+)(?::-([^}]+))?\}")

    def replace(match):
        key = match.group(1)
        default = match.group(2)
        return os.environ.get(key, default if default is not None else "")

    return pattern.sub(replace, text)


# Load secrets
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

    # Ensure LangSmith key is set if present in env
    if "LANGSMITH_API_KEY" in os.environ:
        os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "Deep Agents Memory"

    if "MiniMax_M2_GROUP_ID" in os.environ:
        os.environ["MINIMAX_GROUP_ID"] = os.environ["MiniMax_M2_GROUP_ID"]
    else:
        os.environ["MINIMAX_GROUP_ID"] = "123456"


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


load_secrets()
# init_db() # Assuming DB is initialized by agent.py or externally

# Initialize Checkpointer (MemorySaver for dev)
checkpointer = MemorySaver()

# Create the agent
# Using build_team_graph to match agent.py structure
agent = build_team_graph(checkpointer=checkpointer)
