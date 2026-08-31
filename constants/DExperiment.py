from typing import Final


class DExperiment:
    METHODOLOGY_VERSION: Final[int] = 1
    PROTOCOL_VERSION: Final[int] = 1
    CONTROL_HOST: Final[str] = "127.0.0.1"
    CONTROL_PORT: Final[int] = 51971
    TELEMETRY_HOST: Final[str] = "127.0.0.1"
    TELEMETRY_PORT: Final[int] = 51972
    CLIENT_TIMEOUT_MS: Final[int] = 2_000
    TELEMETRY_HIGH_WATER_MARK: Final[int] = 100
    FIXED_EPOCHS: Final[int] = 1_500
    DEFAULT_EPOCHS: Final[int] = FIXED_EPOCHS
    DEFAULT_LEARNING_RATE: Final[float] = 0.001
    DEFAULT_LEARNING_RATE_STEP: Final[float] = 0.00
    DEFAULT_SEED: Final[int] = 1970
    SEEDS: Final[tuple[int, ...]] = (1970, 1971, 1972)
    VARIATION_FRACTION: Final[float] = 0.05
    MIN_EPOCHS: Final[int] = 50
    MAX_EPOCHS: Final[int] = 100_000
    MIN_LEARNING_RATE: Final[float] = 0.000_001
    MAX_LEARNING_RATE: Final[float] = 0.1
    MAX_QUERY_ROWS: Final[int] = 10_000
    DEFAULT_QUERY_ROWS: Final[int] = 1_000
    MAX_QUERY_RESULT_BYTES: Final[int] = 32_768
    QUERY_TIMEOUT_SECONDS: Final[int] = 5

    CONTROL_ENDPOINT: Final[str] = f"tcp://{CONTROL_HOST}:{CONTROL_PORT}"
    TELEMETRY_ENDPOINT: Final[str] = f"tcp://{TELEMETRY_HOST}:{TELEMETRY_PORT}"
