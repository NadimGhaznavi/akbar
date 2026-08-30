"""Compose and launch Akbar's MCP tool server."""

from tools import documentation, experiments, project
from tools.server import mcp

# Importing each module registers its decorated functions with the shared server.
REGISTERED_MODULES = (documentation, experiments, project)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
