import sys
import os

# Add current directory to sys.path
sys.path.append(os.getcwd())

try:
    print("Attempting to import graph...")
    import graph

    print("Graph imported successfully.")
    print(f"Agent object: {graph.agent}")
except Exception as e:
    print(f"Error importing graph: {e}")
    import traceback

    traceback.print_exc()
