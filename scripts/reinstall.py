#!/usr/bin/env python3
"""Update an existing Akbar installation and restart its service."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constants.DAkbar import DAkbar  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replace the installed Akbar code and restart the service."
    )
    parser.add_argument(
        "--skip-dependencies",
        action="store_true",
        help="do not update packages in the virtual environment",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not DAkbar.INSTALL_ROOT.is_dir():
        print(
            f"reinstall.py: Akbar is not installed in {DAkbar.INSTALL_ROOT}",
            file=sys.stderr,
        )
        return 1

    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "install.py"),
        "--start",
    ]
    if args.skip_dependencies:
        command.append("--skip-dependencies")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as error:
        return error.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
