#!/usr/bin/env python3
"""Remove Akbar, its systemd unit, and its service account."""

from __future__ import annotations

import argparse
import grp
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constants.DAkbar import DAkbar  # noqa: E402


SYSTEMD_DIRECTORY = Path("/etc/systemd/system")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove Akbar, its systemd unit, and its service account."
    )
    return parser.parse_args()


def run(*command: str | Path, check: bool = True) -> None:
    subprocess.run([str(part) for part in command], check=check)


def main() -> int:
    parse_args()
    if os.geteuid() != 0:
        print("uninstall.py: uninstall must be run as root", file=sys.stderr)
        return 1

    if DAkbar.INSTALL_ROOT.exists() and not DAkbar.INSTALL_ROOT.is_dir():
        print(
            f"uninstall.py: refusing to remove non-directory {DAkbar.INSTALL_ROOT}",
            file=sys.stderr,
        )
        return 1

    service_unit = SYSTEMD_DIRECTORY / DAkbar.SERVICE_NAME
    run("systemctl", "disable", "--now", DAkbar.SERVICE_NAME, check=False)

    if service_unit.is_file() or service_unit.is_symlink():
        service_unit.unlink()
    run("systemctl", "daemon-reload")

    if DAkbar.INSTALL_ROOT.is_dir():
        shutil.rmtree(DAkbar.INSTALL_ROOT)

    try:
        pwd.getpwnam(DAkbar.SERVICE_USER)
    except KeyError:
        pass
    else:
        run("userdel", DAkbar.SERVICE_USER)

    try:
        grp.getgrnam(DAkbar.SERVICE_GROUP)
    except KeyError:
        pass
    else:
        run("groupdel", DAkbar.SERVICE_GROUP)

    print("Akbar uninstalled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
