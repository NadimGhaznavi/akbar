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
    parser.add_argument(
        "--purge-data",
        action="store_true",
        help="also remove the MariaDB database, database user, and credentials",
    )
    return parser.parse_args()


def run(*command: str | Path, check: bool = True) -> None:
    subprocess.run([str(part) for part in command], check=check)


def purge_database() -> None:
    mariadb = shutil.which("mariadb")
    if mariadb is None:
        raise FileNotFoundError(
            "MariaDB client not found; database data was not removed"
        )

    sql = f"""
DROP DATABASE IF EXISTS `{DAkbar.DATABASE_NAME}`;
DROP USER IF EXISTS '{DAkbar.DATABASE_USER}'@'{DAkbar.DATABASE_HOST}';
"""
    subprocess.run(
        [mariadb, "--protocol=socket", "--batch"],
        input=sql,
        text=True,
        check=True,
    )
    if DAkbar.DATABASE_ENV_FILE.exists():
        DAkbar.DATABASE_ENV_FILE.unlink()
    if DAkbar.CONFIG_DIRECTORY.is_dir():
        DAkbar.CONFIG_DIRECTORY.rmdir()


def main() -> int:
    args = parse_args()
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

    if args.purge_data:
        try:
            purge_database()
        except (FileNotFoundError, OSError, subprocess.CalledProcessError) as error:
            print(f"uninstall.py: {error}", file=sys.stderr)
            return 1
    elif DAkbar.DATABASE_ENV_FILE.is_file():
        DAkbar.DATABASE_ENV_FILE.chmod(0o600)
        shutil.chown(DAkbar.DATABASE_ENV_FILE, user="root", group="root")
        DAkbar.CONFIG_DIRECTORY.chmod(0o700)
        shutil.chown(DAkbar.CONFIG_DIRECTORY, user="root", group="root")

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
    if not args.purge_data:
        print(
            "MariaDB data and credentials were retained; use --purge-data to remove them"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
