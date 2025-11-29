from langchain_core.tools import tool
import os
import sys

from typing import Dict, Any
import json

@tool
def hello_world(name: str) -> str:
    """
    Returns a personalized greeting for the given name.
    
    Args:
        name (str): The name to greet
        
    Returns:
        str: A greeting message in the format "Hello {name}!"
    """
    return f"Hello {name}!"