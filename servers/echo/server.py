"""Echo MCP server for testing and validation."""

from fastmcp import FastMCP

mcp = FastMCP(name="Echo Server")


@mcp.tool()
def echo(message: str) -> str:
    """Echo back the provided message."""
    return f"Echo: {message}"


@mcp.tool()
def echo_reverse(message: str) -> str:
    """Echo back the provided message in reverse."""
    return f"Echo: {message[::-1]}"


@mcp.tool()
def echo_upper(message: str) -> str:
    """Echo back the provided message in uppercase."""
    return f"Echo: {message.upper()}"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        mcp.http_app(stateless_http=True),
        host="0.0.0.0",
        port=9001,
    )
