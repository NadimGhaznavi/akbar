from pathlib import Path
from typing import Final


class DDatabase:
    ENV_FILE: Final[Path] = Path("/etc/akbar/database.env")
    HOST: Final[str] = "localhost"
    PORT: Final[int] = 3306
    DB_NAME: Final[str] = "akbar"
    USERNAME: Final[str] = "akbar"
