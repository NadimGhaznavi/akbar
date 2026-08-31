"""Experiment control and query MCP tools."""

from experiment.ExperimentClient import ExperimentClient
from experiment.ExperimentProtocol import MessageType
from tools.server import mcp


@mcp.tool()
def ping_experiment_service() -> dict[str, str]:
    """Check that Akbar's experiment service is reachable."""
    return ExperimentClient().request(MessageType.PING)


@mcp.tool()
def start_experiment(
    learning_rate: float,
    epsilon_start: float,
    epsilon_decay: float,
) -> dict:
    """Start an 81-simulation experiment around three submitted values."""
    return ExperimentClient().request(
        MessageType.START_EXPERIMENT,
        {
            "learning_rate": learning_rate,
            "epsilon_start": epsilon_start,
            "epsilon_decay": epsilon_decay,
        },
    )


@mcp.tool()
def get_experiment_config() -> dict:
    """Return the active epoch and learning-rate settings and their limits."""
    return ExperimentClient().request(MessageType.GET_EXPERIMENT_CONFIG)


@mcp.tool()
def set_experiment_learning_rate(learning_rate: float) -> dict:
    """Set the learning rate used by subsequent experiments."""
    return ExperimentClient().request(
        MessageType.SET_EXPERIMENT_CONFIG,
        {"learning_rate": learning_rate},
    )


@mcp.tool()
def get_experiment_database_schema() -> dict:
    """Describe readable database tables and columns for SQL analysis."""
    return ExperimentClient().request(MessageType.GET_DATABASE_SCHEMA)


@mcp.tool()
def query_experiment_database(
    sql: str,
    parameters: dict | list | None = None,
    max_rows: int = 1000,
) -> dict:
    """Execute one arbitrary read-only SQL query against Akbar's database."""
    return ExperimentClient().request(
        MessageType.EXECUTE_READ_QUERY,
        {"sql": sql, "parameters": parameters, "max_rows": max_rows},
    )


@mcp.tool()
def get_experiment_status(experiment_id: str = "") -> dict:
    """Return live or persisted status for an experiment.

    With no ID, returns the most recent experiment held by the service or
    ``ready`` when no experiment has run since startup.
    """
    return ExperimentClient().request(
        MessageType.GET_EXPERIMENT_STATUS,
        experiment_id=experiment_id or None,
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
