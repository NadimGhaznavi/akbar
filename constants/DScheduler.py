from typing import Any, Final

from constants.DAkbar import DAkbar


class DScheduler:
    INITIAL_DELAY_SECONDS: Final[int] = 3
    INTERVAL_SECONDS: Final[int] = 3
    RESULT_HISTORY_LIMIT: Final[int] = 100
    CHAT_COMPLETIONS_URL: Final[str] = (
        f"http://127.0.0.1:{DAkbar.PORT}/v1/chat/completions"
    )
    MODEL_NAME: Final[str] = "akbar"
    CHAT_TIMEOUT_SECONDS: Final[int] = 120
    MAX_COMPLETION_TOKENS: Final[int] = 512
    SYSTEM_PROMPT: Final[str] = (
        "You design the next AI Snake Lab experiment. Review the raw simulation "
        "results and propose learning-rate, initial-epsilon, and epsilon-decay "
        "values for the next experiment. Return only "
        "the required JSON object. Do not call tools or manage the workflow."
    )
    PROPOSAL_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "learning_rate": {"type": "number"},
            "epsilon_start": {"type": "number"},
            "epsilon_decay": {"type": "number"},
            "rationale": {"type": "string", "minLength": 1},
        },
        "required": [
            "learning_rate", "epsilon_start", "epsilon_decay", "rationale"
        ],
        "additionalProperties": False,
    }
