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
        "The scheduled workflow is deterministic. When no experiment is active, "
        "the scheduler loads the current configuration and recent completed "
        "results, then asks the language model once to compare the old runs and "
        "return a structured next configuration with a rationale. Python validates "
        "and persists that proposal, applies it, and starts exactly one experiment. "
        "Interactive users may inspect or control experiments through the tools, "
        "but tool calling is not part of scheduled workflow management."
    )


@mcp.tool()
def doc_06_architecture() -> str:
    """Describe Akbar's operational components and authoritative boundaries."""
    return (
        "Akbar is composed of independent services coordinated through durable "
        "state and narrow local protocols. The scheduler owns a deterministic "
        "workflow: check experiment state, load old results, obtain one structured "
        "configuration proposal from llama.cpp, validate and persist it, then "
        "start one experiment through ZMQ. Interactive web chat reaches the MCP "
        "tool package through llama-server, independently of scheduling. The "
        "experiment service owns simulation execution and "
        "accepts at most one active experiment. MCP tools and the administrative "
        "CLI reach it through the ZMQ control plane; live per-epoch telemetry uses "
        "ZMQ PUB. MariaDB is authoritative for planning rationale, experiment "
        "configuration, lifecycle records, results, and seeds. Simulation state, "
        "model weights, and replay memory remain in process memory. Never add "
        "MariaDB reads or writes within or between simulation epochs. Query tools "
        "for authoritative state instead of relying on chat history."
    )
