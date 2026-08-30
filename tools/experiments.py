"""Experiment control and query MCP tools."""

from experiment.ExperimentClient import ExperimentClient
from experiment.ExperimentProtocol import MessageType
from tools.server import mcp


@mcp.tool()
def ping_experiment_service() -> dict[str, str]:
    """Check that Akbar's experiment service is reachable."""
    return ExperimentClient().request(MessageType.PING)


@mcp.tool()
def start_experiment() -> dict:
    """Start one experiment using the active persisted configuration."""
    return ExperimentClient().request(MessageType.START_EXPERIMENT)


@mcp.tool()
def get_experiment_config() -> dict:
    """Return the active epoch and learning-rate settings and their limits."""
    return ExperimentClient().request(MessageType.GET_EXPERIMENT_CONFIG)


@mcp.tool()
def set_experiment_epochs(epochs: int) -> dict:
    """Set the number of epochs used by subsequent experiments."""
    return ExperimentClient().request(
        MessageType.SET_EXPERIMENT_CONFIG,
        {"epochs": epochs},
    )


@mcp.tool()
def set_experiment_learning_rate(learning_rate: float) -> dict:
    """Set the learning rate used by subsequent experiments."""
    return ExperimentClient().request(
        MessageType.SET_EXPERIMENT_CONFIG,
        {"learning_rate": learning_rate},
    )


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
def list_experiment_results(limit: int = 10) -> dict:
    """List summaries of the most recent completed experiment results."""
    return ExperimentClient().request(
        MessageType.LIST_EXPERIMENT_RESULTS,
        {"limit": limit},
    )


@mcp.tool()
def get_experiment_count() -> dict[str, int]:
    """Return the number of experiments recorded in MariaDB."""
    return ExperimentClient().request(MessageType.GET_EXPERIMENT_COUNT)


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
