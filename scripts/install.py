#!/usr/bin/env python3
"""Destructively install a fresh Akbar deployment."""

from __future__ import annotations

import argparse
import grp
import os
import pwd
import secrets
import shutil
import string
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from constants.DAkbar import DAkbar  # noqa: E402
from constants.DDatabase import DDatabase  # noqa: E402

SYSTEMD_DIRECTORY = Path("/etc/systemd/system")
APPLICATION_FILES = (
    (Path("constants/__init__.py"), Path("constants/__init__.py")),
    (Path("constants/DAkbar.py"), Path("constants/DAkbar.py")),
    (Path("constants/DDatabase.py"), Path("constants/DDatabase.py")),
    (Path("constants/DExperiment.py"), Path("constants/DExperiment.py")),
    (Path("constants/DScheduler.py"), Path("constants/DScheduler.py")),
    (Path("database/__init__.py"), Path("database/__init__.py")),
    (Path("database/Database.py"), Path("database/Database.py")),
    (Path("server/__init__.py"), Path("server/__init__.py")),
    (Path("server/AkbarServer.py"), Path("server/AkbarServer.py")),
    (Path("server/mcp.json"), Path("server/mcp.json")),
    (Path("scheduler/__init__.py"), Path("scheduler/__init__.py")),
    (
        Path("scheduler/SchedulerServer.py"),
        Path("scheduler/SchedulerServer.py"),
    ),
    (
        Path("scheduler/PlanningRepository.py"),
        Path("scheduler/PlanningRepository.py"),
    ),
    (Path("experiment/__init__.py"), Path("experiment/__init__.py")),
    (
        Path("experiment/ExperimentServer.py"),
        Path("experiment/ExperimentServer.py"),
    ),
    (
        Path("experiment/ExperimentClient.py"),
        Path("experiment/ExperimentClient.py"),
    ),
    (
        Path("experiment/ExperimentConfig.py"),
        Path("experiment/ExperimentConfig.py"),
    ),
    (
        Path("experiment/ExperimentProtocol.py"),
        Path("experiment/ExperimentProtocol.py"),
    ),
    (
        Path("experiment/ExperimentRepository.py"),
        Path("experiment/ExperimentRepository.py"),
    ),
    (
        Path("experiment/ExperimentRunner.py"),
        Path("experiment/ExperimentRunner.py"),
    ),
    (
        Path("experiment/ExperimentState.py"),
        Path("experiment/ExperimentState.py"),
    ),
    (Path("snake_lab/__init__.py"), Path("snake_lab/__init__.py")),
    (
        Path("snake_lab/SnakeExperiment.py"),
        Path("snake_lab/SnakeExperiment.py"),
    ),
    (Path("snake_lab/game/__init__.py"), Path("snake_lab/game/__init__.py")),
    (
        Path("snake_lab/game/SnakeGame.py"),
        Path("snake_lab/game/SnakeGame.py"),
    ),
    (
        Path("snake_lab/models/__init__.py"),
        Path("snake_lab/models/__init__.py"),
    ),
    (
        Path("snake_lab/models/LinearQModel.py"),
        Path("snake_lab/models/LinearQModel.py"),
    ),
    (
        Path("snake_lab/training/__init__.py"),
        Path("snake_lab/training/__init__.py"),
    ),
    (
        Path("snake_lab/training/QTrainer.py"),
        Path("snake_lab/training/QTrainer.py"),
    ),
    (
        Path("snake_lab/training/ReplayMemory.py"),
        Path("snake_lab/training/ReplayMemory.py"),
    ),
    (Path("tools/__init__.py"), Path("tools/__init__.py")),
    (Path("tools/__main__.py"), Path("tools/__main__.py")),
    (Path("tools/server.py"), Path("tools/server.py")),
    (Path("tools/project.py"), Path("tools/project.py")),
    (Path("tools/documentation.py"), Path("tools/documentation.py")),
    (Path("tools/experiments.py"), Path("tools/experiments.py")),
    (Path("scripts/akbar-cli.py"), Path("scripts/akbar-cli.py")),
    (Path("scripts/install.py"), Path("scripts/install.py")),
    (Path("scripts/upgrade.py"), Path("scripts/upgrade.py")),
)
DEPENDENCY_FILES = (Path("requirements.txt"), Path("pyproject.toml"))
OBSOLETE_SERVICE_NAMES = ("akbar-agentd.service",)
OBSOLETE_APPLICATION_PATHS = (Path("agent"), Path("orchestration"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Destructively recreate Akbar, including its MariaDB database and "
            "credentials."
        )
    )
    parser.add_argument(
        "--prefix",
        type=Path,
        default=DAkbar.INSTALL_ROOT,
        help=f"installation directory (default: {DAkbar.INSTALL_ROOT})",
    )
    parser.add_argument(
        "--skip-dependencies",
        action="store_true",
        help="create the virtual environment without installing dependencies",
    )
    parser.add_argument(
        "--no-service",
        action="store_true",
        help="do not install the systemd unit",
    )
    parser.add_argument(
        "--enable",
        action="store_true",
        help="enable the systemd service at boot",
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="start or restart the service after installation",
    )
    return parser.parse_args()


def run(*command: str | Path, check: bool = True) -> None:
    subprocess.run([str(part) for part in command], check=check)


def validate_prefix(prefix: Path) -> Path:
    prefix = prefix.expanduser()
    if not prefix.is_absolute() or len(prefix.parts) < 3:
        raise ValueError("--prefix must be a specific absolute directory")
    resolved = prefix.resolve(strict=False)
    if resolved == PROJECT_ROOT or PROJECT_ROOT.is_relative_to(resolved):
        raise ValueError("--prefix cannot contain the source checkout")
    return resolved


def require_root() -> None:
    if os.geteuid() != 0:
        raise PermissionError("the production installation must be run as root")


def validate_source(install_systemd_service: bool) -> None:
    for source_path, _ in APPLICATION_FILES:
        source = PROJECT_ROOT / source_path
        if not source.is_file():
            raise FileNotFoundError(f"application file not found: {source}")

    if install_systemd_service:
        for service_name in DAkbar.SERVICE_NAMES:
            service_unit = PROJECT_ROOT / "systemd" / service_name
            if not service_unit.is_file():
                raise FileNotFoundError(f"systemd unit not found: {service_unit}")


def ensure_service_account(prefix: Path) -> None:
    try:
        grp.getgrnam(DAkbar.SERVICE_GROUP)
    except KeyError:
        run("groupadd", "--system", DAkbar.SERVICE_GROUP)

    try:
        pwd.getpwnam(DAkbar.SERVICE_USER)
    except KeyError:
        run(
            "useradd",
            "--system",
            "--gid",
            DAkbar.SERVICE_GROUP,
            "--home-dir",
            prefix,
            "--shell",
            "/usr/sbin/nologin",
            DAkbar.SERVICE_USER,
        )


def write_database_environment(password: str) -> None:
    DAkbar.CONFIG_DIRECTORY.mkdir(parents=True, exist_ok=True, mode=0o750)
    DAkbar.CONFIG_DIRECTORY.chmod(0o750)
    shutil.chown(
        DAkbar.CONFIG_DIRECTORY,
        user="root",
        group=DAkbar.SERVICE_GROUP,
    )

    content = (
        f"AKBAR_DB_HOST={DDatabase.HOST}\n"
        f"AKBAR_DB_PORT={DDatabase.PORT}\n"
        f"AKBAR_DB_NAME={DDatabase.DB_NAME}\n"
        f"AKBAR_DB_USER={DDatabase.USERNAME}\n"
        f"AKBAR_DB_PASSWORD={password}\n"
    )
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=DAkbar.CONFIG_DIRECTORY,
        prefix=".database.env.",
        delete=False,
    ) as temporary_file:
        temporary_file.write(content)
        temporary_path = Path(temporary_file.name)

    temporary_path.chmod(0o640)
    shutil.chown(temporary_path, user="root", group=DAkbar.SERVICE_GROUP)
    temporary_path.replace(DDatabase.ENV_FILE)


def mariadb_client() -> str:
    mariadb = shutil.which("mariadb")
    if mariadb is None:
        raise FileNotFoundError(
            "MariaDB client not found; install MariaDB server and client first"
        )
    return mariadb


def destroy_database() -> None:
    if DAkbar.CONFIG_DIRECTORY.is_symlink():
        raise ValueError(
            f"refusing symlinked config directory: {DAkbar.CONFIG_DIRECTORY}"
        )
    sql = f"""
DROP DATABASE IF EXISTS `{DDatabase.DB_NAME}`;
DROP USER IF EXISTS '{DDatabase.USERNAME}'@'{DDatabase.HOST}';
"""
    subprocess.run(
        [mariadb_client(), "--protocol=socket", "--batch"],
        input=sql,
        text=True,
        check=True,
    )
    if DAkbar.CONFIG_DIRECTORY.is_dir():
        shutil.rmtree(DAkbar.CONFIG_DIRECTORY)


def provision_database() -> None:
    mariadb = mariadb_client()

    alphabet = string.ascii_letters + string.digits
    password = "".join(secrets.choice(alphabet) for _ in range(48))

    sql = f"""
CREATE DATABASE IF NOT EXISTS `{DDatabase.DB_NAME}`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '{DDatabase.USERNAME}'@'{DDatabase.HOST}'
    IDENTIFIED BY '{password}';
ALTER USER '{DDatabase.USERNAME}'@'{DDatabase.HOST}'
    IDENTIFIED BY '{password}';
GRANT ALL PRIVILEGES ON `{DDatabase.DB_NAME}`.*
    TO '{DDatabase.USERNAME}'@'{DDatabase.HOST}';
"""
    subprocess.run(
        [mariadb, "--protocol=socket", "--batch"],
        input=sql,
        text=True,
        check=True,
    )
    write_database_environment(password)


def destroy_services() -> None:
    for service_name in reversed((*DAkbar.SERVICE_NAMES, *OBSOLETE_SERVICE_NAMES)):
        run("systemctl", "disable", "--now", service_name, check=False)
        service_unit = SYSTEMD_DIRECTORY / service_name
        if service_unit.is_file() or service_unit.is_symlink():
            service_unit.unlink()
    run("systemctl", "daemon-reload")


def destroy_service_account() -> None:
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


def destroy_installation(prefix: Path) -> None:
    if prefix.is_symlink():
        raise ValueError(f"refusing symlinked installation prefix: {prefix}")
    if prefix.exists() and not prefix.is_dir():
        raise ValueError(f"refusing non-directory installation prefix: {prefix}")
    if prefix.is_dir():
        shutil.rmtree(prefix)


def install_application(prefix: Path) -> None:
    prefix.mkdir(parents=True, exist_ok=True, mode=0o755)
    prefix.chmod(0o755)

    for source_path, destination_path in APPLICATION_FILES:
        source = PROJECT_ROOT / source_path
        destination = prefix / destination_path
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        destination.parent.chmod(0o755)
        shutil.copy2(source, destination)
        destination.chmod(
            0o755 if destination_path.parent == Path("scripts") else 0o644
        )

    for relative_path in DEPENDENCY_FILES:
        source = PROJECT_ROOT / relative_path
        if source.is_file():
            destination = prefix / relative_path
            shutil.copy2(source, destination)
            destination.chmod(0o644)


def install_environment(prefix: Path, skip_dependencies: bool) -> None:
    environment = prefix / DAkbar.VENV_DIRECTORY
    venv.EnvBuilder(with_pip=True, upgrade_deps=False).create(environment)

    requirements = prefix / "requirements.txt"
    if requirements.is_file() and not skip_dependencies:
        run(environment / "bin" / "python", "-m", "pip", "install", "-r", requirements)


def install_services(prefix: Path, enable: bool, start: bool) -> None:
    if prefix != DAkbar.INSTALL_ROOT:
        raise ValueError(
            "systemd installation requires the production prefix; use --no-service "
            "with an alternate prefix"
        )

    for service_name in OBSOLETE_SERVICE_NAMES:
        obsolete_unit = SYSTEMD_DIRECTORY / service_name
        if obsolete_unit.is_file() or obsolete_unit.is_symlink():
            obsolete_unit.unlink()

    for service_name in DAkbar.SERVICE_NAMES:
        source = PROJECT_ROOT / "systemd" / service_name
        destination = SYSTEMD_DIRECTORY / service_name
        shutil.copy2(source, destination)
        destination.chmod(0o644)
    run("systemctl", "daemon-reload")

    if enable:
        for service_name in DAkbar.SERVICE_NAMES:
            run("systemctl", "enable", service_name)
    if start:
        for service_name in DAkbar.SERVICE_NAMES:
            run("systemctl", "restart", service_name)


def main() -> int:
    args = parse_args()
    try:
        prefix = validate_prefix(args.prefix)
        if args.no_service and (args.enable or args.start):
            raise ValueError("--enable and --start cannot be used with --no-service")
        if not args.no_service and prefix != DAkbar.INSTALL_ROOT:
            raise ValueError(
                "systemd installation requires /opt/akbar; use --no-service "
                "with an alternate prefix"
            )
        validate_source(install_systemd_service=not args.no_service)

        if prefix == DAkbar.INSTALL_ROOT:
            require_root()
            destroy_services()
            destroy_installation(prefix)
            destroy_database()
            destroy_service_account()
            ensure_service_account(prefix)
            provision_database()
        else:
            destroy_installation(prefix)

        install_application(prefix)
        install_environment(prefix, args.skip_dependencies)

        if not args.no_service:
            install_services(prefix, args.enable, args.start)
    except (FileNotFoundError, PermissionError, ValueError, subprocess.CalledProcessError) as error:
        print(f"install.py: {error}", file=sys.stderr)
        return 1

    print(f"Akbar installed in {prefix}")
    if not args.start and not args.no_service:
        print(f"Start it with: systemctl start {' '.join(DAkbar.SERVICE_NAMES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
