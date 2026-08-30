from pathlib import Path
from typing import Final


class DAkbar:
    INSTALL_ROOT: Final[Path] = Path("/opt/akbar")
    VENV_DIRECTORY: Final[str] = ".venv"
    SERVICE_NAME: Final[str] = "akbar.service"
    SERVICE_USER: Final[str] = "akbar"
    SERVICE_GROUP: Final[str] = "akbar"
    LLAMA_SERVER: Final[Path] = Path("/opt/dev/llama.cpp/build/bin/llama-server")
    MODEL: Final[Path] = Path(
        "/opt/dev/models/quantized/Qwen3.5-4B-Q4_K_M.gguf"
    )
    CONTEXT_SIZE: Final[int] = 16_384
    HOST: Final[str] = "0.0.0.0"
    PORT: Final[int] = 51970
    VERSION: Final[str]="0.0.1"
