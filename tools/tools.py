"""MCP tools exposed by Akbar."""

from mcp.server import MCPServer

from constants.DAkbar import DAkbar

mcp = MCPServer("akbar")


@mcp.tool()
def get_project_version() -> str:
    """Return the current Akbar project version."""
    return DAkbar.VERSION


if __name__ == "__main__":
    mcp.run()
