"""Self-documentation MCP tools for Akbar."""

from tools.server import mcp


@mcp.tool()
def doc_00_intro() -> str:
    """Read first: describe Akbar's role and available operating guidance."""
    return (
        "Your role is to run deliberate, evidence-driven AI Snake Lab "
        "experiments. Use the numbered doc tools for operating guidance. Inspect "
        "authoritative service and database-backed results through tools instead "
        "of assuming state from conversation. Run at most one experiment at a "
        "time and use accumulated results to justify each next decision."
    )


@mcp.tool()
def doc_01_overview() -> str:
    """Return a short overview of Akbar."""
    return (
        "An experiment represents one simulation run of AI Snake Lab. "
        "The goal is to find a hyperparameter "
        "configuration that maximizes the score. "
    )


@mcp.tool()
def doc_02_configure_experiment() -> str:
    """Return a short description of how to configure an experiment."""
    return (
        "Call get_experiment_config first to inspect the active configuration "
        "and its current limits. Use set_experiment_epochs or "
        "set_experiment_learning_rate to change one value for subsequent runs. "
        "Configuration changes are rejected while an experiment is active."
    )


@mcp.tool()
def doc_03_run_experiment() -> str:
    """Return a short description of how to run an experiment."""
    return (
        "Call start_experiment once and retain the returned experiment ID. "
        "Do not issue another start while an experiment is queued or running. "
        "Use get_experiment_status to monitor it. After its status becomes "
        "completed, use get_experiment_result to retrieve the persisted result. "
        "Use list_experiment_results to discover recent completed runs."
    )


@mcp.tool()
def doc_04_review_results() -> str:
    """Return a short description of how to review previous results."""
    return (
        "Call list_experiment_results to retrieve compact summaries of recent "
        "completed experiments. The optional limit defaults to 10 and must be "
        "between 1 and 100. Compare the configuration and score metrics in the "
        "summaries, then pass an experiment ID to get_experiment_result when "
        "you need that run's full persisted result."
    )


@mcp.tool()
def doc_05_design_next_experiment() -> str:
    """Describe the safe evidence-driven next-experiment decision cycle."""
    return (
        "First call get_experiment_status. If an experiment is queued or running, "
        "inspect it and do not start another. Otherwise call "
        "list_experiment_results, retrieve full results when useful, and compare "
        "learning rates, epoch counts, and score metrics. Form a specific "
        "hypothesis and rationale for the next run. Change only justified active "
        "configuration values, then call start_experiment exactly once. Finish by "
        "reporting the evidence, chosen configuration, rationale, and returned "
        "experiment ID; the agent-turn response is persisted in MariaDB."
    )


@mcp.tool()
def doc_06_architecture() -> str:
    """Describe Akbar's operational components and authoritative boundaries."""
    return (
        "Akbar is composed of independent services coordinated through durable "
        "state and narrow local protocols. The scheduler only enqueues agent "
        "turns in MariaDB. The agent worker independently claims those turns, "
        "uses llama.cpp for inference, and executes validated function calls "
        "through MCP tools. Interactive web chat reaches the same MCP tool "
        "package through llama-server. The experiment service owns simulation "
        "execution and "
        "accepts at most one active experiment. MCP tools and the administrative "
        "CLI reach it through the ZMQ control plane; live per-epoch telemetry uses "
        "ZMQ PUB. MariaDB is authoritative for durable agent turns, experiment "
        "configuration, lifecycle records, results, and seeds. Simulation state, "
        "model weights, and replay memory remain in process memory. Never add "
        "MariaDB reads or writes within or between simulation epochs. Query tools "
        "for authoritative state instead of relying on chat history."
    )
