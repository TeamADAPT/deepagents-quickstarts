from langchain_community.tools import DuckDuckGoSearchRun
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper


def get_research_tools():
    """Returns a list of research tools."""
    search = DuckDuckGoSearchRun()

    wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())

    return [search, wikipedia]
