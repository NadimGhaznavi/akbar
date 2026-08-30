#!/usr/bin/env python3
"""Independently process durable Akbar agent turns from MariaDB."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Protocol

import httpx
from pymysql.err import MySQLError

from agent.AkbarAgent import AgentError, AkbarAgent, LlamaChatClient, MCPToolGateway
from constants.DAgent import DAgent
from constants.DAkbar import DAkbar
from orchestration.TurnRepository import MariaDBTurnRepository, TurnRepository

LOGGER = logging.getLogger("akbar.agentd")


class AgentRunner(Protocol):
    async def run(
        self,
        prompt: str,
        *,
        require_experiment_resolution: bool = False,
    ) -> str: ...


class AgentWorker:
    def __init__(
        self,
        repository: TurnRepository,
        agent: AgentRunner,
        poll_interval_seconds: float = DAgent.POLL_INTERVAL_SECONDS,
        turn_timeout_seconds: float = DAgent.TURN_TIMEOUT_SECONDS,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("poll interval must be positive")
        if turn_timeout_seconds <= 0:
            raise ValueError("turn timeout must be positive")
        self.repository = repository
        self.agent = agent
        self.poll_interval_seconds = poll_interval_seconds
        self.turn_timeout_seconds = turn_timeout_seconds

    async def run(self) -> None:
        while True:
            processed = await self.process_one()
            if not processed:
                await asyncio.sleep(self.poll_interval_seconds)

    async def process_one(self) -> bool:
        turn = await asyncio.to_thread(self.repository.claim_next)
        if turn is None:
            return False
        turn_id = turn["turn_id"]
        LOGGER.info("processing agent turn %s from %s", turn_id, turn["source"])
        try:
            async with asyncio.timeout(self.turn_timeout_seconds):
                response = await self.agent.run(
                    turn["prompt"],
                    require_experiment_resolution=turn["source"] == "scheduler",
                )
        except asyncio.CancelledError:
            await asyncio.to_thread(
                self.repository.finish,
                turn_id,
                "interrupted",
                None,
                "Agent worker stopped during execution",
            )
            raise
        except TimeoutError:
            await asyncio.to_thread(
                self.repository.finish,
                turn_id,
                "failed",
                None,
                "Agent turn exceeded its deadline",
            )
            LOGGER.error("agent turn %s exceeded its deadline", turn_id)
        except (AgentError, httpx.HTTPError, MySQLError, OSError) as error:
            await asyncio.to_thread(
                self.repository.finish,
                turn_id,
                "failed",
                None,
                str(error),
            )
            LOGGER.error("agent turn %s failed: %s", turn_id, error)
        else:
            await asyncio.to_thread(
                self.repository.finish,
                turn_id,
                "completed",
                response,
                None,
            )
            LOGGER.info("agent turn %s completed", turn_id)
        return True


def _environment_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


async def serve() -> None:
    repository = MariaDBTurnRepository()
    await asyncio.to_thread(repository.initialize)
    await asyncio.to_thread(repository.mark_interrupted)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(shutdown_signal, stop_event.set)

    chat = LlamaChatClient()
    tool_gateway = MCPToolGateway(
        command=sys.executable,
        args=["-m", "tools"],
        cwd=DAkbar.INSTALL_ROOT,
    )
    try:
        async with tool_gateway:
            worker = AgentWorker(
                repository,
                AkbarAgent(chat, tool_gateway),
                poll_interval_seconds=_environment_float(
                    "AKBAR_AGENT_POLL_INTERVAL_SECONDS",
                    DAgent.POLL_INTERVAL_SECONDS,
                ),
                turn_timeout_seconds=_environment_float(
                    "AKBAR_AGENT_TURN_TIMEOUT_SECONDS",
                    DAgent.TURN_TIMEOUT_SECONDS,
                ),
            )
            worker_task = asyncio.create_task(worker.run())
            stop_task = asyncio.create_task(stop_event.wait())
            done, _pending = await asyncio.wait(
                {worker_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if worker_task in done:
                stop_task.cancel()
                await worker_task
            else:
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass
    finally:
        await chat.close()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(serve())
    except (MySQLError, ValueError, OSError) as error:
        LOGGER.error("agent worker failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
