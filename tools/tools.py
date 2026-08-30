"""MCP tools exposed by Akbar."""

from mcp.server import MCPServer

from constants.DAkbar import DAkbar
from experiment.ExperimentClient import ExperimentClient
from experiment.ExperimentProtocol import MessageType

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


@mcp.tool()
def ping_experiment_service() -> dict[str, str]:
    """Check that Akbar's experiment service is reachable."""
    return ExperimentClient().request(MessageType.PING)


@mcp.tool()
def start_experiment() -> dict:
    """Start one experiment using the service's fixed default configuration."""
    return ExperimentClient().request(MessageType.START_EXPERIMENT)


@mcp.tool()
def get_experiment_status(experiment_id: str = "") -> dict:
    """Return live or persisted status for an experiment.

    With no ID, returns the most recent experiment held by the service.
    """
    return ExperimentClient().request(
        MessageType.GET_EXPERIMENT_STATUS,
        experiment_id=experiment_id or None,
    )


@mcp.tool()
def get_experiment_result(experiment_id: str) -> dict:
    """Return the completed, persisted result for an experiment ID."""
    return ExperimentClient().request(
        MessageType.GET_EXPERIMENT_RESULT,
        experiment_id=experiment_id,
    )


@mcp.tool()
def get_current_highscore(experiment_id: str = "") -> dict:
    """Return the current in-memory highscore without querying MariaDB."""
    return ExperimentClient().request(
        MessageType.GET_CURRENT_HIGHSCORE,
        experiment_id=experiment_id or None,
    )


@mcp.tool()
def stop_experiment(experiment_id: str = "") -> dict:
    """Request cancellation of the active experiment."""
    return ExperimentClient().request(
        MessageType.STOP_EXPERIMENT,
        experiment_id=experiment_id or None,
    )


if __name__ == "__main__":
    mcp.run()
