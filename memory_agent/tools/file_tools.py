from langchain_community.agent_toolkits import FileManagementToolkit
import os


def get_file_tools():
    """Returns a list of file management tools."""
    # Full system access as requested
    root_dir = "/"
    toolkit = FileManagementToolkit(root_dir=root_dir)
    return toolkit.get_tools()
