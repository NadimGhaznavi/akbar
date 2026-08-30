"""Self-documentation MCP tools."""

from tools.server import mcp


@mcp.tool()
def doc_00_intro() -> str:
    """Return a short introduction to the project."""
    return (
        "This project uses an AI assistent to run experiments in the AI Snake Lab. "
        "This Qwen based assistant and this project have been named Akbar."
    )


@mcp.tool()
def doc_01_overview() -> str:
    """Return a short overview of the project goal."""
    return (
        "An experiment is a controlled batch of 135 AI Snake Lab simulations. "
        "Akbar proposes three hyperparameter values and reviews the raw stored "
        "simulation results without the experiment service judging them."
    )


@mcp.tool()
def doc_02_configure_experiment() -> str:
    """Return a short description of how to configure an experiment."""
    return (
        "Submit learning_rate, epsilon_start, and epsilon_decay to "
        "start_experiment. The service varies each value by 5 percent to form "
        "a 3 x 3 x 3 grid, then runs every configuration with five fixed seeds. "
        "Every simulation runs for exactly 1500 epochs."
    )


@mcp.tool()
def doc_03_run_experiment() -> str:
    """Return a short description of how to run an experiment."""
    return (
        "Call start_experiment once with the three baseline hyperparameters and "
        "retain the returned experiment ID. "
        "Do not issue another start while an experiment is queued or running. "
        "Use get_experiment_status to monitor it. After its status becomes "
        "completed, query its individual simulation rows in MariaDB."
    )


@mcp.tool()
def doc_04_review_results() -> str:
    """Return a short description of how to review previous results."""
    return (
        "Call get_experiment_database_schema to discover tables and columns, "
        "then call query_experiment_database with one read-only SELECT or CTE. "
        "Filtering, joins, grouping, aggregation, and ordering are available; "
        "their interpretation belongs to Akbar. Use PyMySQL placeholders (%s "
        "or %(name)s) and pass values separately in parameters."
    )


@mcp.tool()
def doc_05_design_next_experiment() -> str:
    """Describe the safe evidence-driven next-experiment decision cycle."""
    return (
        "The scheduled workflow is deterministic. When no experiment is active, "
        "the scheduler loads raw completed simulation rows, then asks the language "
        "model once for learning-rate, initial-epsilon, and epsilon-decay values. "
        "Python validates and persists that proposal and starts one experiment. "
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
