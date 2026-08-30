"""Bounded placeholder experiment runner."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from experiment.ExperimentConfig import ExperimentConfig

TelemetryCallback = Callable[[dict[str, Any]], Awaitable[None]]


class ExperimentCancelled(Exception):
    """The active experiment was cancelled by a control request."""


class ExperimentRunner:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    async def run(
        self,
        stop_event: asyncio.Event,
        publish_telemetry: TelemetryCallback,
    ) -> dict[str, Any]:
        from snake_lab.SnakeExperiment import SnakeExperiment

        return await SnakeExperiment(self.config).run(
            stop_event,
            publish_telemetry,
        )
