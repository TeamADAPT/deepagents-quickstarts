from langchain_core.tools import tool
import os
import sys

@tool
def math_tool(a: int, b: int) -> str:
    """
    Takes two integers and returns their sum as a string.
    
    Args:
        a: First integer
        b: Second integer
    
    Returns:
        String representation of the sum of a and b
    """
    result = a + b
    return str(result)