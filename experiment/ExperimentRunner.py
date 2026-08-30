"""Bounded placeholder experiment runner."""

from __future__ import annotations

import asyncio
import random
import statistics
import time
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
        rng = random.Random(self.config.seed)
        scores: list[int] = []
        highscore = 0
        started = time.monotonic()

        for epoch in range(1, self.config.epochs + 1):
            if stop_event.is_set():
                raise ExperimentCancelled()

            if self.config.epoch_delay:
                try:
                    await asyncio.wait_for(
                        stop_event.wait(), timeout=float(self.config.epoch_delay)
                    )
                except asyncio.TimeoutError:
                    pass
                if stop_event.is_set():
                    raise ExperimentCancelled()

            score = rng.randint(0, 10) + (epoch // 10)
            highscore = max(highscore, score)
            scores.append(score)
            await publish_telemetry(
                {
                    "epoch": epoch,
                    "score": score,
                    "highscore": highscore,
                    "progress": epoch / self.config.epochs,
                    "elapsed_seconds": round(time.monotonic() - started, 6),
                }
            )

        return {
            "epochs": self.config.epochs,
            "highscore": highscore,
            "average_score": round(statistics.fmean(scores), 6),
            "elapsed_seconds": round(time.monotonic() - started, 6),
        }
