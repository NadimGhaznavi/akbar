#!/usr/bin/env python3
"""Run Akbar's deterministic experiment-planning workflow."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from dataclasses import asdict, dataclass
from typing import Any, Protocol

import httpx
from pymysql.err import MySQLError

from constants.DScheduler import DScheduler
from experiment.ExperimentClient import ExperimentClient, ExperimentClientError
from experiment.ExperimentProtocol import MessageType
from scheduler.PlanningRepository import MariaDBPlanningRepository, PlanningRepository

LOGGER = logging.getLogger("akbar.scheduler")


class PlanningError(RuntimeError):
    """The inference service returned an unusable experiment proposal."""


@dataclass(frozen=True, slots=True)
class ExperimentProposal:
    learning_rate: float
    epsilon_start: float
    epsilon_decay: float
    rationale: str

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        config: dict[str, Any],
    ) -> ExperimentProposal:
        if set(data) != {
            "learning_rate", "epsilon_start", "epsilon_decay", "rationale"
        }:
            raise PlanningError(
                "proposal must contain learning_rate, epsilon_start, "
                "epsilon_decay, and rationale"
            )
        learning_rate = data["learning_rate"]
        epsilon_start = data["epsilon_start"]
        epsilon_decay = data["epsilon_decay"]
        rationale = data["rationale"]
        for name, value in (
            ("learning_rate", learning_rate),
            ("epsilon_start", epsilon_start),
            ("epsilon_decay", epsilon_decay),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise PlanningError(f"proposal {name} must be a number")
        if not isinstance(rationale, str) or not rationale.strip():
            raise PlanningError("proposal rationale must be non-empty text")
        limits = config["limits"]
        rate_limits = limits["learning_rate"]
        if not (
            rate_limits["minimum"] <= float(learning_rate) <= rate_limits["maximum"]
        ):
            raise PlanningError(
                "proposal learning_rate is outside the configured limits"
            )
        if not 0 < float(epsilon_start) <= 1:
            raise PlanningError("proposal epsilon_start must be above 0 and at most 1")
        if not 0 < float(epsilon_decay) < 1:
            raise PlanningError("proposal epsilon_decay must be between 0 and 1")
        return cls(
            float(learning_rate),
            float(epsilon_start),
            float(epsilon_decay),
            rationale.strip(),
        )


class Planner(Protocol):
    async def propose(
        self,
        config: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> ExperimentProposal: ...


class ExperimentControl(Protocol):
    def request(
        self,
        message_type: MessageType,
        payload: dict[str, Any] | None = None,
        experiment_id: str | None = None,
    ) -> dict[str, Any]: ...


class LlamaPlanner:
    def __init__(
        self,
        url: str = DScheduler.CHAT_COMPLETIONS_URL,
        model: str = DScheduler.MODEL_NAME,
        timeout_seconds: float = DScheduler.CHAT_TIMEOUT_SECONDS,
        client: Any | None = None,
    ) -> None:
        self.url = url
        self.model = model
        self.client = client or httpx.AsyncClient(timeout=timeout_seconds)

    async def close(self) -> None:
        await self.client.aclose()

    async def propose(
        self,
        config: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> ExperimentProposal:
        evidence = json.dumps(
            {"active_configuration": config, "previous_experiments": results},
            separators=(",", ":"),
        )
        response = await self.client.post(
            self.url,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": DScheduler.SYSTEM_PROMPT},
                    {"role": "user", "content": evidence},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "experiment_proposal",
                        "strict": True,
                        "schema": DScheduler.PROPOSAL_SCHEMA,
                    },
                },
                "max_tokens": DScheduler.MAX_COMPLETION_TOKENS,
                "chat_template_kwargs": {"enable_thinking": False},
                "stream": False,
            },
        )
        response.raise_for_status()
        choice: Any = None
        message: Any = None
        try:
            payload = response.json()
            choice = payload["choices"][0]
            message = choice["message"]
            content = message["content"]
            if not isinstance(content, str) or not content:
                raise PlanningError("proposal content is empty")
            proposal_data = json.loads(content)
            if not isinstance(proposal_data, dict):
                raise PlanningError("inference proposal must be a JSON object")
        except (
            KeyError,
            IndexError,
            TypeError,
            json.JSONDecodeError,
            PlanningError,
        ) as error:
            content = message.get("content") if isinstance(message, dict) else None
            reasoning = (
                message.get("reasoning_content") if isinstance(message, dict) else None
            )
            finish_reason = (
                choice.get("finish_reason") if isinstance(choice, dict) else None
            )
            LOGGER.error(
                "invalid proposal response: finish_reason=%r content_length=%d "
                "reasoning_length=%d content_preview=%r",
                finish_reason,
                len(content) if isinstance(content, str) else 0,
                len(reasoning) if isinstance(reasoning, str) else 0,
                content[:200] if isinstance(content, str) else None,
            )
            raise PlanningError(
                "inference service returned invalid proposal JSON"
            ) from error
        return ExperimentProposal.from_dict(proposal_data, config)


class Scheduler:
    """Execute one explicit planning-and-launch state machine at a time."""

    def __init__(
        self,
        experiment: ExperimentControl,
        planner: Planner,
        plans: PlanningRepository,
        *,
        initial_delay_seconds: float = DScheduler.INITIAL_DELAY_SECONDS,
        interval_seconds: float = DScheduler.INTERVAL_SECONDS,
    ) -> None:
        if initial_delay_seconds < 0:
            raise ValueError("initial delay must not be negative")
        if interval_seconds <= 0:
            raise ValueError("interval must be positive")
        self.experiment = experiment
        self.planner = planner
        self.plans = plans
        self.initial_delay_seconds = initial_delay_seconds
        self.interval_seconds = interval_seconds

    async def run_once(self) -> str | None:
        status = await self._request(MessageType.GET_EXPERIMENT_STATUS)
        if status.get("status") in {"queued", "running"}:
            LOGGER.info("experiment is %s; schedule tick skipped", status["status"])
            return None

        config = await self._request(MessageType.GET_EXPERIMENT_CONFIG)
        history = await self._request(
            MessageType.EXECUTE_READ_QUERY,
            {
                "sql": (
                    "SELECT simulation_id, experiment_id, seed, epochs, "
                    "learning_rate, epsilon_start, epsilon_decay, highscore, "
                    "average_score, average_loss, total_moves, replay_size, "
                    "elapsed_seconds, "
                    "completed_at FROM simulation_runs "
                    "WHERE status = 'completed' ORDER BY completed_at DESC LIMIT %s"
                ),
                "parameters": [DScheduler.RESULT_HISTORY_LIMIT],
                "max_rows": DScheduler.RESULT_HISTORY_LIMIT,
            },
        )
        results = history.get("rows")
        if not isinstance(results, list):
            raise PlanningError("experiment service returned invalid result history")

        LOGGER.info("requesting proposal using %d previous results", len(results))
        proposal = await self.planner.propose(config, results)
        proposal_data = asdict(proposal)
        plan_id = await asyncio.to_thread(
            self.plans.create,
            proposal_data,
            results,
        )
        try:
            await self._request(
                MessageType.SET_EXPERIMENT_CONFIG,
                {
                    "learning_rate": proposal.learning_rate,
                    "epsilon_start": proposal.epsilon_start,
                    "epsilon_decay": proposal.epsilon_decay,
                },
            )
            accepted = await self._request(
                MessageType.START_EXPERIMENT,
                {
                    "learning_rate": proposal.learning_rate,
                    "epsilon_start": proposal.epsilon_start,
                    "epsilon_decay": proposal.epsilon_decay,
                },
            )
            experiment_id = accepted["experiment_id"]
            await asyncio.to_thread(self.plans.mark_started, plan_id, experiment_id)
        except Exception as error:
            await asyncio.to_thread(self.plans.mark_failed, plan_id, str(error))
            raise
        LOGGER.info("started experiment %s from plan %s", experiment_id, plan_id)
        return experiment_id

    async def _request(
        self,
        message_type: MessageType,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self.experiment.request, message_type, payload)

    async def run(self, stop_event: asyncio.Event) -> None:
        delay = self.initial_delay_seconds
        while not await _wait_or_stop(stop_event, delay):
            try:
                await self.run_once()
            except (
                ExperimentClientError,
                PlanningError,
                httpx.HTTPError,
                MySQLError,
                OSError,
            ) as error:
                LOGGER.error("scheduled experiment cycle failed: %s", error)
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
    plans = MariaDBPlanningRepository()
    await asyncio.to_thread(plans.initialize)
    planner = LlamaPlanner()
    scheduler = Scheduler(
        ExperimentClient(),
        planner,
        plans,
        initial_delay_seconds=_environment_float(
            "AKBAR_SCHEDULER_INITIAL_DELAY_SECONDS",
            DScheduler.INITIAL_DELAY_SECONDS,
        ),
        interval_seconds=_environment_float(
            "AKBAR_SCHEDULER_INTERVAL_SECONDS",
            DScheduler.INTERVAL_SECONDS,
        ),
    )
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(shutdown_signal, stop_event.set)
    try:
        await scheduler.run(stop_event)
    finally:
        await planner.close()


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
