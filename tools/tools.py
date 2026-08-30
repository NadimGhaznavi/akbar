"""MCP tools exposed by Akbar."""

from mcp.server import MCPServer

from constants.DAkbar import DAkbar

mcp = MCPServer("akbar")


@mcp.tool()
def get_project_version() -> str:
    """Return the current Akbar project version."""
    return DAkbar.VERSION


@mcp.tool()
def get_project_info() -> dict[str, str]:
    """Return information about Akbar and its administrator.

    Use the administrator's name when greeting or directly addressing the user.
    """
    return {
        "project_name": "Akbar",
        "project_version": DAkbar.VERSION,
        "project_description": (
            "Akbar is a locally hosted AI agent backed by a Qwen language model. "
            "Its long-term purpose is to run, evaluate, and improve AI Snake Lab "
            "experiments through a structured and reproducible process."
        ),
        "administrator_name": "Nadim-Daniel Ghaznavi",
        "web_chat_user": "Nadim-Daniel Ghaznavi",
        "preferred_greeting": "Hi Nadim, what can I help you with?",
    }


if __name__ == "__main__":
    mcp.run()
