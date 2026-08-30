from pathlib import Path
from typing import Final


class DAkbar:
    INSTALL_ROOT: Final[Path] = Path("/opt/akbar")
    VENV_DIRECTORY: Final[str] = ".venv"
    SERVICE_NAME: Final[str] = "akbar.service"
    EXPERIMENT_SERVICE_NAME: Final[str] = "akbar-experimentd.service"
    AGENT_SERVICE_NAME: Final[str] = "akbar-agentd.service"
    SCHEDULER_SERVICE_NAME: Final[str] = "akbar-scheduler.service"
    SERVICE_NAMES: Final[tuple[str, ...]] = (
        EXPERIMENT_SERVICE_NAME,
        SERVICE_NAME,
        AGENT_SERVICE_NAME,
        SCHEDULER_SERVICE_NAME,
    )
    SERVICE_USER: Final[str] = "akbar"
    SERVICE_GROUP: Final[str] = "akbar"
    CONFIG_DIRECTORY: Final[Path] = Path("/etc/akbar")
    LLAMA_SERVER: Final[Path] = Path("/opt/dev/llama.cpp/build/bin/llama-server")
    MODEL: Final[Path] = Path(
        "/opt/dev/models/quantized/Qwen3.5-4B-Q4_K_M.gguf"
    )
    MCP_SERVERS_CONFIG: Final[Path] = INSTALL_ROOT / "server" / "mcp.json"
    CONTEXT_SIZE: Final[int] = 32_768
    REASONING_BUDGET: Final[int] = 2_048
    HOST: Final[str] = "0.0.0.0"
    PORT: Final[int] = 51970
    VERSION: Final[str] = "0.10.6"
