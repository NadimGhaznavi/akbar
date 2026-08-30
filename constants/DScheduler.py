from typing import Final


class DScheduler:
    INITIAL_DELAY_SECONDS: Final[int] = 15
    INTERVAL_SECONDS: Final[int] = 15
    PROMPT: Final[str] = (
        "Continue the AI Snake Lab investigation. First inspect the current "
        "experiment state. If an experiment is queued or running, report its "
        "status and do not start another. Otherwise, review recent completed "
        "results, compare their configurations and score metrics, and design the "
        "next deliberate learning-rate experiment. Explain the evidence and "
        "rationale, update the persisted configuration if appropriate, and start "
        "exactly one experiment. In your final response, record the decision, "
        "configuration, rationale, and resulting experiment ID."
    )
