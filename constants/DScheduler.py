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
        "You design the next AI Snake Lab learning-rate experiment. Review the "
        "provided previous experiments, compare their configurations and score "
        "metrics, and propose one deliberate next configuration. Return only "
        "the required JSON object. Do not call tools or manage the workflow."
    )
    PROPOSAL_SCHEMA: Final[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "epochs": {"type": "integer"},
            "learning_rate": {"type": "number"},
            "rationale": {"type": "string", "minLength": 1},
        },
        "required": ["epochs", "learning_rate", "rationale"],
        "additionalProperties": False,
    }
