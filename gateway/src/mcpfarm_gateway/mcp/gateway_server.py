"""FastMCP gateway instance with dynamic mounting."""

from fastmcp import FastMCP

# The single gateway MCP server that all backends get mounted onto.
# Clients connect to this one endpoint and see all tools from all servers.
gateway_mcp = FastMCP(name="MCPFarm Gateway")


@gateway_mcp.tool()
def farm_ping() -> str:
    """Check if the MCPFarm gateway is alive."""
    return "MCPFarm gateway is running."
