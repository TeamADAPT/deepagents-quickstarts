from langchain_core.tools import tool

# Global flag to signal reload
_reload_requested = False


def request_reload():
    global _reload_requested
    _reload_requested = True


def check_reload_request():
    global _reload_requested
    if _reload_requested:
        _reload_requested = False
        return True
    return False


@tool
def reload_system() -> str:
    """
    Reloads the agent system, refreshing all tools and configurations.
    Use this after creating new tools or modifying system settings.
    """
    request_reload()
    return "System reload requested. The agent will re-initialize after this turn."


def get_admin_tools():
    return [reload_system]
