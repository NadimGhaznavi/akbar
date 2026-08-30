from typing import Final


class DExperiment:
    PROTOCOL_VERSION: Final[int] = 1
    CONTROL_HOST: Final[str] = "127.0.0.1"
    CONTROL_PORT: Final[int] = 51971
    TELEMETRY_HOST: Final[str] = "127.0.0.1"
    TELEMETRY_PORT: Final[int] = 51972
    CLIENT_TIMEOUT_MS: Final[int] = 2_000
    TELEMETRY_HIGH_WATER_MARK: Final[int] = 100
    DEFAULT_EPOCHS: Final[int] = 20
    DEFAULT_SEED: Final[int] = 1970
    MAX_EPOCHS: Final[int] = 1_000_000

    CONTROL_ENDPOINT: Final[str] = f"tcp://{CONTROL_HOST}:{CONTROL_PORT}"
    TELEMETRY_ENDPOINT: Final[str] = f"tcp://{TELEMETRY_HOST}:{TELEMETRY_PORT}"
    CONTROL_BIND_ENDPOINT: Final[str] = f"tcp://{CONTROL_HOST}:{CONTROL_PORT}"
    TELEMETRY_BIND_ENDPOINT: Final[str] = f"tcp://{TELEMETRY_HOST}:{TELEMETRY_PORT}"
