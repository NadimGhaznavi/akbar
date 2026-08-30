from typing import Final

from constants.DAkbar import DAkbar


class DAgent:
    CHAT_COMPLETIONS_URL: Final[str] = (
        f"http://127.0.0.1:{DAkbar.PORT}/v1/chat/completions"
    )
    MODEL_NAME: Final[str] = "akbar"
    MAX_TOOL_ROUNDS: Final[int] = 8
    MAX_TOOL_CALLS: Final[int] = 20
    CHAT_TIMEOUT_SECONDS: Final[int] = 300
    TURN_TIMEOUT_SECONDS: Final[int] = 1_800
    POLL_INTERVAL_SECONDS: Final[int] = 5
