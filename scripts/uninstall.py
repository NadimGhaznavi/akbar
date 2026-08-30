#!/usr/bin/env python3
"""Destructively remove Akbar and all Akbar-owned data."""

from __future__ import annotations

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
from constants.DDatabase import DDatabase  # noqa: E402


SYSTEMD_DIRECTORY = Path("/etc/systemd/system")


def run(*command: str | Path, check: bool = True) -> None:
    subprocess.run([str(part) for part in command], check=check)


def purge_database() -> None:
    if DAkbar.CONFIG_DIRECTORY.is_symlink():
        raise ValueError(
            f"refusing symlinked config directory: {DAkbar.CONFIG_DIRECTORY}"
        )
    mariadb = shutil.which("mariadb")
    if mariadb is None:
        raise FileNotFoundError(
            "MariaDB client not found; database data was not removed"
        )

    sql = f"""
DROP DATABASE IF EXISTS `{DDatabase.DB_NAME}`;
DROP USER IF EXISTS '{DDatabase.USERNAME}'@'{DDatabase.HOST}';
"""
    subprocess.run(
        [mariadb, "--protocol=socket", "--batch"],
        input=sql,
        text=True,
        check=True,
    )
    if DAkbar.CONFIG_DIRECTORY.is_dir():
        shutil.rmtree(DAkbar.CONFIG_DIRECTORY)


def main() -> int:
    if len(sys.argv) > 1:
        print("uninstall.py: this command accepts no arguments", file=sys.stderr)
        return 1
    if os.geteuid() != 0:
        print("uninstall.py: uninstall must be run as root", file=sys.stderr)
        return 1

    if DAkbar.INSTALL_ROOT.exists() and not DAkbar.INSTALL_ROOT.is_dir():
        print(
            f"uninstall.py: refusing to remove non-directory {DAkbar.INSTALL_ROOT}",
            file=sys.stderr,
        )
        return 1

    for service_name in reversed(DAkbar.SERVICE_NAMES):
        run("systemctl", "disable", "--now", service_name, check=False)
        service_unit = SYSTEMD_DIRECTORY / service_name
        if service_unit.is_file() or service_unit.is_symlink():
            service_unit.unlink()
    run("systemctl", "daemon-reload")

    if DAkbar.INSTALL_ROOT.is_dir():
        shutil.rmtree(DAkbar.INSTALL_ROOT)

    try:
        purge_database()
    except (FileNotFoundError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"uninstall.py: {error}", file=sys.stderr)
        return 1

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

    print("Akbar and all Akbar-owned data uninstalled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
