"""Calculator MCP server for multi-tool testing."""

import math

from fastmcp import FastMCP

mcp = FastMCP(name="Calculator Server")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b. Returns error message if b is zero."""
    if b == 0:
        raise ValueError("Division by zero")
    return a / b


@mcp.tool()
def power(base: float, exponent: float) -> float:
    """Raise base to the power of exponent."""
    return math.pow(base, exponent)


@mcp.tool()
def sqrt(n: float) -> float:
    """Calculate the square root of a number."""
    if n < 0:
        raise ValueError("Cannot take square root of negative number")
    return math.sqrt(n)


@mcp.tool()
def factorial(n: int) -> int:
    """Calculate the factorial of a non-negative integer."""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n > 170:
        raise ValueError("Number too large for factorial")
    return math.factorial(n)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        mcp.http_app(stateless_http=True),
        host="0.0.0.0",
        port=9001,
    )
