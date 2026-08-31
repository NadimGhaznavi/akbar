from typing import Any, Final

from constants.DAkbar import DAkbar


class DScheduler:
    INITIAL_DELAY_SECONDS: Final[int] = 3
    INTERVAL_SECONDS: Final[int] = 3
    MAX_INVESTIGATION_ROUNDS: Final[int] = 8
    MAX_INVESTIGATION_TOOL_CALLS: Final[int] = 16
    CHAT_COMPLETIONS_URL: Final[str] = (
        f"http://127.0.0.1:{DAkbar.PORT}/v1/chat/completions"
    )
    MODEL_NAME: Final[str] = "akbar"
    CHAT_TIMEOUT_SECONDS: Final[int] = 120
    MAX_COMPLETION_TOKENS: Final[int] = 512
    SYSTEM_PROMPT: Final[str] = (
        "You design the next AI Snake Lab experiment. Begin at the orientation "
        "intranet homepage / and consult the pages relevant to your task. First "
        "discover the MariaDB "
        "schema, then investigate it using the provided read-only SQL tool before "
        "proposing anything. If a query returns an error, correct the SQL and retry. "
        "You choose the queries: establish the complete relevant population, "
        "verify experiment/status/seed/configuration coverage, and analyze all "
        "relevant observations rather than an arbitrary subset. Use LIMIT only "
        "for exploration or presentation, never as the evidentiary population. "
        "When the evidence is sufficient, explain that the investigation is "
        "complete. Do not start experiments or attempt database writes."
    )
    EVALUATION_SYSTEM_PROMPT: Final[str] = (
        "You evaluate one completed AI Snake Lab experiment. Begin at the "
        "orientation intranet homepage / and consult relevant guidance. Discover "
        "the MariaDB schema, then use read-only SQL to verify the complete relevant "
        "population, lifecycle status, seed coverage, and configuration coverage. "
        "Judge only the persisted rationale and predeclared success criterion. Do "
        "not propose or start another experiment and do not attempt database writes."
    )
    PLANNER_TOOLS: Final[list[dict[str, Any]]] = [
        {
            "type": "function",
            "function": {
                "name": "doc_browser",
                "description": (
                    "Browse the read-only Akbar orientation intranet. Begin at / "
                    "and follow its internal links."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string", "default": "/"}},
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_database_schema",
                "description": "Describe readable MariaDB tables and columns.",
                "parameters": {"type": "object", "properties": {},
                               "additionalProperties": False},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_experiment_database",
                "description": "Execute one arbitrary read-only SELECT or CTE.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "minLength": 1},
                        "parameters": {"type": ["object", "array", "null"]},
                        "max_rows": {"type": "integer", "minimum": 1,
                                     "maximum": 10_000},
                    },
                    "required": ["sql"],
                    "additionalProperties": False,
                },
            },
        },
    ]
    PROPOSAL_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "learning_rate": {"type": "number"},
            "epsilon_start": {"type": "number"},
            "epsilon_decay": {"type": "number"},
            "rationale": {"type": "string", "minLength": 1},
            "success_criterion": {"type": "string", "minLength": 1},
        },
        "required": [
            "learning_rate", "epsilon_start", "epsilon_decay", "rationale",
            "success_criterion",
        ],
        "additionalProperties": False,
    }
    EVALUATION_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["pass", "fail", "inconclusive"],
            },
            "conclusion": {"type": "string", "minLength": 1},
        },
        "required": ["verdict", "conclusion"],
        "additionalProperties": False,
    }
    DUPLICATE_PROPOSAL_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            **PROPOSAL_SCHEMA["properties"],
            "duplicate_experiment_reason": {
                "type": ["string", "null"],
            },
        },
        "required": [
            *PROPOSAL_SCHEMA["required"],
            "duplicate_experiment_reason",
        ],
        "additionalProperties": False,
    }
