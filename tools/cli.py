#!/usr/bin/env python3
"""Trusted menu-driven interface to Akbar's experiment control plane."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

# When installed as /opt/akbar/bin/akbar-cli, make the application packages
# beside bin/ importable without relying on the caller's working directory.
APPLICATION_ROOT = Path(__file__).resolve().parent.parent
INSTALLED_PYTHON = APPLICATION_ROOT / ".venv" / "bin" / "python"
if (
    INSTALLED_PYTHON.is_file()
    and Path(sys.prefix).resolve() != INSTALLED_PYTHON.parent.parent.resolve()
):
    os.execv(
        INSTALLED_PYTHON,
        [str(INSTALLED_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]],
    )
if str(APPLICATION_ROOT) not in sys.path:
    sys.path.insert(0, str(APPLICATION_ROOT))

from experiment.ExperimentClient import (  # noqa: E402
    ExperimentClient,
    ExperimentClientError,
)
from experiment.ExperimentProtocol import MessageType  # noqa: E402

InputFunction = Callable[[str], str]


def short_id(experiment_id: str) -> str:
    return f"[{experiment_id[-4:]}]"


def safe_for_display(value: Any) -> Any:
    """Replace full experiment UUIDs before anything reaches the terminal."""
    if isinstance(value, dict):
        return {
            key: short_id(item) if key == "experiment_id" and isinstance(item, str)
            else safe_for_display(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [safe_for_display(item) for item in value]
    return value


class AkbarCLI:
    MENU = """
Akbar Experiment CLI

1. Check experiment service
2. Count persisted experiments
3. Start experiment
4. Show experiment status
5. Show current highscore
6. Show persisted result
7. Stop experiment
8. Quit
"""

    def __init__(
        self,
        client: ExperimentClient | None = None,
        input_function: InputFunction = input,
        output: TextIO = sys.stdout,
    ) -> None:
        self.client = client or ExperimentClient()
        self.input = input_function
        self.output = output
        self.last_experiment_id: str | None = None

    def run(self) -> int:
        actions = {
            "1": self.ping,
            "2": self.count,
            "3": self.start,
            "4": self.status,
            "5": self.highscore,
            "6": self.result,
            "7": self.stop,
        }
        while True:
            self._write(self.MENU.rstrip())
            try:
                choice = self.input("Select: ").strip()
                if choice in {"8", "q", "quit", "exit"}:
                    self._write("Goodbye.")
                    return 0
                action = actions.get(choice)
                if action is None:
                    self._write("Unknown selection.")
                    continue
                action()
            except (ExperimentClientError, ValueError) as error:
                self._write(f"Error: {error}")
            except (EOFError, KeyboardInterrupt):
                self._write("\nGoodbye.")
                return 0

    def ping(self) -> None:
        self._show(self.client.request(MessageType.PING))

    def count(self) -> None:
        self._show(self.client.request(MessageType.GET_EXPERIMENT_COUNT))

    def start(self) -> None:
        response = self.client.request(MessageType.START_EXPERIMENT)
        self._remember(response)
        self._show(response)

    def status(self) -> None:
        response = self.client.request(
            MessageType.GET_EXPERIMENT_STATUS,
            experiment_id=self._select_id(required=False),
        )
        self._remember(response)
        self._show(response)

    def highscore(self) -> None:
        response = self.client.request(
            MessageType.GET_CURRENT_HIGHSCORE,
            experiment_id=self._select_id(required=False),
        )
        self._remember(response)
        self._show(response)

    def result(self) -> None:
        response = self.client.request(
            MessageType.GET_EXPERIMENT_RESULT,
            experiment_id=self._select_id(required=True),
        )
        self._remember(response)
        self._show(response)

    def stop(self) -> None:
        experiment_id = self._select_id(required=True)
        confirmation = self.input(
            f"Stop experiment {short_id(experiment_id)}? [y/N]: "
        ).strip().lower()
        if confirmation not in {"y", "yes"}:
            self._write("Stop cancelled.")
            return
        response = self.client.request(
            MessageType.STOP_EXPERIMENT,
            experiment_id=experiment_id,
        )
        self._remember(response)
        self._show(response)

    def _select_id(self, required: bool) -> str | None:
        default = (
            f" (Enter for {short_id(self.last_experiment_id)})"
            if self.last_experiment_id
            else ""
        )
        entered = self.input(f"Experiment ID or 4-character suffix{default}: ").strip()
        if not entered:
            if self.last_experiment_id:
                return self.last_experiment_id
            if required:
                raise ValueError("an experiment ID is required")
            return None
        if len(entered) == 4:
            response = self.client.request(
                MessageType.RESOLVE_EXPERIMENT_ID,
                {"suffix": entered},
            )
            experiment_id = response["experiment_id"]
            self.last_experiment_id = experiment_id
            return experiment_id
        return entered

    def _remember(self, response: dict[str, Any]) -> None:
        experiment_id = response.get("experiment_id")
        if isinstance(experiment_id, str):
            self.last_experiment_id = experiment_id

    def _show(self, response: dict[str, Any]) -> None:
        self._write(json.dumps(safe_for_display(response), indent=2, sort_keys=True))

    def _write(self, message: str) -> None:
        print(message, file=self.output)


def main() -> int:
    return AkbarCLI().run()


if __name__ == "__main__":
    raise SystemExit(main())
