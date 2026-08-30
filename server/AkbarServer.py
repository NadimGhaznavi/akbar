#!/usr/bin/env python3
"""Launch the llama.cpp server used by Akbar."""

from __future__ import annotations

import os
import sys

from constants.DAkbar import DAkbar


def build_command() -> list[str]:
    """Return the llama-server command for the configured Akbar model."""
    return [
        str(DAkbar.LLAMA_SERVER),
        "-m",
        str(DAkbar.MODEL),
        "--ctx-size",
        str(DAkbar.CONTEXT_SIZE),
        "--host",
        DAkbar.HOST,
        "--port",
        str(DAkbar.PORT),
    ]


def validate_configuration() -> None:
    """Fail with a useful message when a required runtime file is missing."""
    if not DAkbar.LLAMA_SERVER.is_file():
        raise FileNotFoundError(f"llama-server not found: {DAkbar.LLAMA_SERVER}")
    if not os.access(DAkbar.LLAMA_SERVER, os.X_OK):
        raise PermissionError(f"llama-server is not executable: {DAkbar.LLAMA_SERVER}")
    if not DAkbar.MODEL.is_file():
        raise FileNotFoundError(f"model not found: {DAkbar.MODEL}")


def main() -> int:
    try:
        validate_configuration()
        command = build_command()
        os.execv(command[0], command)
    except (FileNotFoundError, PermissionError, OSError) as error:
        print(f"AkbarServer: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
