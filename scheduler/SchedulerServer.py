#!/usr/bin/env python3
"""Periodically enqueue durable Akbar agent turns in MariaDB."""

from __future__ import annotations

import asyncio
import logging
import os
import signal

from pymysql.err import MySQLError

from constants.DScheduler import DScheduler
from orchestration.TurnRepository import MariaDBTurnRepository, TurnRepository

LOGGER = logging.getLogger("akbar.scheduler")


class Scheduler:
    """Produce scheduled work without owning or supervising its consumer."""

    def __init__(
        self,
        repository: TurnRepository,
        *,
        prompt: str = DScheduler.PROMPT,
        initial_delay_seconds: float = DScheduler.INITIAL_DELAY_SECONDS,
        interval_seconds: float = DScheduler.INTERVAL_SECONDS,
    ) -> None:
        if initial_delay_seconds < 0:
            raise ValueError("initial delay must not be negative")
        if interval_seconds <= 0:
            raise ValueError("interval must be positive")
        self.repository = repository
        self.prompt = prompt
        self.initial_delay_seconds = initial_delay_seconds
        self.interval_seconds = interval_seconds

    async def enqueue_once(self) -> str | None:
        """Queue work unless MariaDB already contains an active turn."""
        return await asyncio.to_thread(
            self.repository.enqueue,
            self.prompt,
            "scheduler",
        )

    async def run(self, stop_event: asyncio.Event) -> None:
        delay = self.initial_delay_seconds
        while not await _wait_or_stop(stop_event, delay):
            try:
                turn_id = await self.enqueue_once()
                if turn_id is None:
                    LOGGER.info("active agent turn exists; schedule tick skipped")
                else:
                    LOGGER.info("queued scheduled agent turn %s", turn_id)
            except (MySQLError, OSError) as error:
                LOGGER.error("could not queue scheduled agent turn: %s", error)
            delay = self.interval_seconds


async def _wait_or_stop(stop_event: asyncio.Event, delay: float) -> bool:
    if stop_event.is_set():
        return True
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=delay)
    except TimeoutError:
        return False
    return True


def _environment_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


async def serve() -> None:
    repository = MariaDBTurnRepository()
    await asyncio.to_thread(repository.initialize)
    scheduler = Scheduler(
        repository,
        initial_delay_seconds=_environment_float(
            "AKBAR_SCHEDULER_INITIAL_DELAY_SECONDS",
            DScheduler.INITIAL_DELAY_SECONDS,
        ),
        interval_seconds=_environment_float(
            "AKBAR_SCHEDULER_INTERVAL_SECONDS",
            DScheduler.INTERVAL_SECONDS,
        ),
        prompt=os.getenv("AKBAR_SCHEDULER_PROMPT", DScheduler.PROMPT),
    )
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(shutdown_signal, stop_event.set)
    await scheduler.run(stop_event)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(serve())
    except (MySQLError, ValueError, OSError) as error:
        LOGGER.error("scheduler failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
