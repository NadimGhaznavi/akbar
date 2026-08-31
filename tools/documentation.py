"""MCP entry point for Akbar's internal orientation site."""

from tools.AknetBrowser import load_aknet_page
from tools.server import mcp


@mcp.tool()
def doc_browser(url: str = "/") -> str:
    """Browse Akbar's orientation intranet; begin at the homepage URL ``/``."""
    return load_aknet_page(url)
