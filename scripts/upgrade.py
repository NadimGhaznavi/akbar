#!/usr/bin/env python3
"""Upgrade Akbar application code while preserving all MariaDB data."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constants.DAkbar import DAkbar  # noqa: E402
from constants.DDatabase import DDatabase  # noqa: E402
from scripts.install import (  # noqa: E402
    APPLICATION_FILES,
    DEPENDENCY_FILES,
    install_application,
    install_services,
    validate_source,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upgrade Akbar code and dependencies without modifying MariaDB "
            "data, its account, or credentials."
        )
    )
    parser.add_argument(
        "--skip-dependencies",
        action="store_true",
        help="do not update packages in the existing virtual environment",
    )
    return parser.parse_args()


def run(*command: str | Path, check: bool = True) -> None:
    subprocess.run([str(part) for part in command], check=check)


def validate_installation() -> None:
    if os.geteuid() != 0:
        raise PermissionError("upgrade must be run as root")
    if not DAkbar.INSTALL_ROOT.is_dir() or DAkbar.INSTALL_ROOT.is_symlink():
        raise FileNotFoundError(
            f"Akbar is not safely installed in {DAkbar.INSTALL_ROOT}"
        )
    environment_python = (
        DAkbar.INSTALL_ROOT / DAkbar.VENV_DIRECTORY / "bin" / "python"
    )
    if not environment_python.is_file():
        raise FileNotFoundError(f"virtual environment not found: {environment_python}")
    if DDatabase.ENV_FILE.is_symlink() or not DDatabase.ENV_FILE.is_file():
        raise FileNotFoundError(
            f"database credentials not found: {DDatabase.ENV_FILE}"
        )


def stop_services() -> None:
    for service_name in reversed(DAkbar.SERVICE_NAMES):
        run("systemctl", "stop", service_name, check=False)


def remove_installed_runtime(install_root: Path = DAkbar.INSTALL_ROOT) -> None:
    """Remove only files owned by the application manifest, never data."""
    targets = {
        destination.parts[0]
        for _, destination in APPLICATION_FILES
        if destination.parts[0] != DAkbar.VENV_DIRECTORY
    }
    targets.update(path.parts[0] for path in DEPENDENCY_FILES)
    for target in targets:
        destination = install_root / target
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        elif destination.exists() or destination.is_symlink():
            destination.unlink()


def update_dependencies(skip_dependencies: bool) -> None:
    if skip_dependencies:
        return
    environment_python = (
        DAkbar.INSTALL_ROOT / DAkbar.VENV_DIRECTORY / "bin" / "python"
    )
    run(
        environment_python,
        "-m",
        "pip",
        "install",
        "-r",
        DAkbar.INSTALL_ROOT / "requirements.txt",
    )


def main() -> int:
    args = parse_args()
    try:
        validate_source(install_systemd_service=True)
        validate_installation()
        stop_services()
        remove_installed_runtime()
        install_application(DAkbar.INSTALL_ROOT)
        update_dependencies(args.skip_dependencies)
        install_services(DAkbar.INSTALL_ROOT, enable=False, start=True)
    except (
        FileNotFoundError,
        PermissionError,
        ValueError,
        OSError,
        subprocess.CalledProcessError,
    ) as error:
        print(f"upgrade.py: {error}", file=sys.stderr)
        return 1

    print("Akbar upgraded; MariaDB data and credentials were preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
