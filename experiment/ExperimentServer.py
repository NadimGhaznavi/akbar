#!/usr/bin/env python3
"""Akbar experiment service entry point."""

from __future__ import annotations

import asyncio
import logging
import signal


LOG = logging.getLogger("akbar.experimentd")


async def serve() -> None:
    """Run the experiment service until systemd requests shutdown."""
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(shutdown_signal, stop_event.set)

    LOG.info("Akbar experiment service started")
    await stop_event.wait()
    LOG.info("Akbar experiment service stopped")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(serve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
