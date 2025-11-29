from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
import os


def get_db_tools(db_url: str, llm=None):
    """Returns a list of database tools."""
    if not db_url:
        return []

    db = SQLDatabase.from_uri(db_url)

    # We need an LLM for the toolkit to function (it uses it to describe tables etc)
    # If not provided, we'll try to create a lightweight one or fail gracefully
    if llm is None:
        # Fallback or error, but for now let's assume it's passed or we create a simple one
        # This might be circular if we try to import the main agent's LLM.
        # Ideally, pass the LLM in.
        pass

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    return toolkit.get_tools()
