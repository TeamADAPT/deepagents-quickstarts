import os
import sys
from langchain_core.tools import tool

# Directory to store generated tools
TOOLS_DIR = "/adapt/platform/novaops/frameworks/lang/deepagents-quickstarts/memory_agent/tools/generated"
os.makedirs(TOOLS_DIR, exist_ok=True)

# Ensure the generated tools directory is in the path
if TOOLS_DIR not in sys.path:
    sys.path.append(TOOLS_DIR)


@tool
def create_tool(name: str, description: str, code: str, dependencies: str = "") -> str:
    """
    Creates a new tool dynamically.

    Args:
        name: The name of the tool (e.g., 'weather_checker').
        description: A description of what the tool does.
        code: The Python code for the tool. Must contain a function decorated with @tool.
        dependencies: Comma-separated list of pip packages to install.
    """
    try:
        # 1. Install dependencies if any
        if dependencies:
            import subprocess

            pkgs = [p.strip() for p in dependencies.split(",") if p.strip()]
            if pkgs:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + pkgs)

        # 2. Save the code to a file
        filename = f"{name}.py"
        filepath = os.path.join(TOOLS_DIR, filename)

        # Add standard imports if missing
        header = "from langchain_core.tools import tool\nimport os\nimport sys\n\n"
        full_code = header + code

        with open(filepath, "w") as f:
            f.write(full_code)

        # 3. Verify the tool by trying to import it
        # We need to invalidate caches to ensure we import the new module
        import importlib

        if name in sys.modules:
            del sys.modules[name]

        # Try importing
        # Since TOOLS_DIR is in sys.path, we can import by filename (minus .py)
        # But we need to be careful about package structure.
        # Ideally we'd import `tools.generated.{name}` but since we added TOOLS_DIR to path:
        module = importlib.import_module(name)

        # Check if it has a tool
        has_tool = False
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, "name") and hasattr(attr, "description"):
                has_tool = True
                break

        if not has_tool:
            return f"Error: No tool found in the generated code. Did you decorate a function with @tool?"

        return f"Successfully created tool '{name}' at {filepath}. You can now use it."

    except Exception as e:
        return f"Error creating tool: {str(e)}"


def get_meta_tools():
    """Returns meta-tools and any dynamically generated tools."""
    tools = [create_tool]

    # Load generated tools
    import importlib.util

    if not os.path.exists(TOOLS_DIR):
        return tools

    for filename in os.listdir(TOOLS_DIR):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            try:
                # Invalidate cache to ensure fresh reload
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)

                module = sys.modules.get(module_name)
                if module:
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        # Check if it looks like a LangChain tool
                        if (
                            hasattr(attr, "name")
                            and hasattr(attr, "description")
                            and hasattr(attr, "invoke")
                        ):
                            # Avoid duplicates if imported multiple times
                            if attr not in tools:
                                tools.append(attr)
            except Exception as e:
                print(f"Error loading tool from {filename}: {e}")

    return tools
