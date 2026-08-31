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
        "An experiment is a controlled batch of 81 AI Snake Lab simulations. "
        "Akbar proposes three hyperparameter values and reviews the raw stored "
        "simulation results without the experiment service judging them."
    )


@mcp.tool()
def doc_02_configure_experiment() -> str:
    """Return a short description of how to configure an experiment."""
    return (
        "Submit learning_rate, epsilon_start, and epsilon_decay to "
        "start_experiment. The service varies each value by 5 percent to form "
        "a 3 x 3 x 3 grid, then runs every configuration with three fixed seeds. "
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
        "the scheduler requires the language model to investigate MariaDB through "
        "schema discovery and read-only SQL before proposing learning-rate, initial-"
        "epsilon, and epsilon-decay values. Akbar chooses the evidence queries; the "
        "scheduler does not preselect a result sample. Python validates and persists "
        "the proposal and its SQL evidence, then starts one experiment. "
        "Interactive users may inspect or control experiments through the tools, "
        "but tool calling is not part of scheduled workflow management."
    )


@mcp.tool()
def doc_06_architecture() -> str:
    """Describe Akbar's operational components and authoritative boundaries."""
    return (
        "Akbar is composed of independent services coordinated through durable "
        "state and narrow local protocols. The scheduler owns a deterministic "
        "workflow: check experiment state, let llama.cpp investigate MariaDB with "
        "bounded read-only SQL, obtain one structured configuration proposal, "
        "validate and persist its decision and evidence, then "
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


@mcp.tool()
def doc_07_actual_experiment() -> str:
    """Describe the Snake reinforcement-learning simulation being studied."""
    return (
        "The experimental subject is a deterministic, headless Snake game and a "
        "compact DQN-style reinforcement-learning agent implemented with NumPy. "
        "Each epoch is one complete game. The agent observes 11 binary features: "
        "danger straight, right, and left; its current direction; and whether food "
        "is left, right, above, or below the head. It chooses one of three relative "
        "actions: continue straight, turn right, or turn left. Rewards are +10 for "
        "food, -10 for collision or exceeding the move limit, +1 for moving closer "
        "to food, and -1 for moving farther away. The Q-function is one linear "
        "11-input, 3-output layer with a bias; it has no hidden layers and is not "
        "currently a multilayer feed-forward neural network. Training uses an "
        "epsilon-greedy policy, one-step temporal-difference targets, discount "
        "factor gamma, gradient clipping, and bounded replay memory. Each transition "
        "is trained immediately, followed by one replay-memory batch after each "
        "game when enough samples exist. There is no separate target network. Every "
        "simulation creates a fresh model and replay memory from its assigned seed; "
        "weights and replay data remain in memory and are discarded afterward. The "
        "stored simulation result contains its full configuration plus epoch, score, "
        "loss, move, replay-size, and runtime measurements."
    )


@mcp.tool()
def doc_08_data_discipline() -> str:
    """Explain the evidence-coverage standard for experiment conclusions."""
    return (
        "Do not draw experimental conclusions from an arbitrary or incomplete "
        "subset of simulation rows, including only the first, last, highest, or "
        "lowest observations. Before "
        "analysis, use the database tools to establish the complete relevant "
        "population: count simulations by experiment and status, identify every "
        "configuration and seed represented, and check for failed, cancelled, "
        "running, or missing runs. A normally completed experiment is designed to "
        "contain 81 completed simulations: 27 hyperparameter configurations times "
        "three seeds. Analyze all available rows for every experiment being compared, "
        "or perform SQL calculations over that full population. LIMIT is appropriate "
        "for schema exploration, debugging, or presenting examples, but a limited "
        "result set is not adequate evidence for a scientific conclusion. Always "
        "report the experiment IDs, filters, row counts, status coverage, seed "
        "coverage, and configuration coverage used in an interpretation. If the "
        "population is incomplete, say so and defer conclusions that depend on the "
        "missing observations."
    )
