from langchain_experimental.tools import PythonREPLTool
from langchain_community.tools import ShellTool


def get_code_tools():
    """Returns a list of code execution tools."""
    python_repl = PythonREPLTool()
    shell_tool = ShellTool()
    return [python_repl, shell_tool]
