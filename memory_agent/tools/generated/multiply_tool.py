from langchain_core.tools import tool
import os
import sys

@tool
def multiply_tool(a: int, b: int) -> str:
    """
    Takes two integers 'a' and 'b' and returns their product as a string.
    
    Args:
        a: First integer
        b: Second integer
    
    Returns:
        String representation of the product of a and b
    """
    return str(a * b)