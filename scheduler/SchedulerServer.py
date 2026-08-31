#!/usr/bin/env python3
"""Run Akbar's deterministic experiment-planning workflow."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from dataclasses import asdict, dataclass
from collections.abc import Awaitable, Callable
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


@dataclass(frozen=True, slots=True)
class PlanningDecision:
    proposal: ExperimentProposal
    evidence: list[dict[str, Any]]


DatabaseToolExecutor = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class Planner(Protocol):
    async def propose(
        self,
        config: dict[str, Any],
        execute_tool: DatabaseToolExecutor,
    ) -> PlanningDecision: ...


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
        execute_tool: DatabaseToolExecutor,
    ) -> PlanningDecision:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": DScheduler.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "active_configuration": config,
                        "task": "Investigate all relevant data and design the next experiment.",
                    },
                    separators=(",", ":"),
                ),
            },
        ]
        evidence: list[dict[str, Any]] = []
        tool_call_count = 0
        successful_query_count = 0
        schema_discovered = False
        for _ in range(DScheduler.MAX_INVESTIGATION_ROUNDS):
            message = await self._request_message(
                messages,
                tools=DScheduler.DATABASE_TOOLS,
            )
            tool_calls = message.get("tool_calls")
            assistant_message = {
                "role": "assistant",
                "content": message.get("content"),
            }
            if "tool_calls" in message:
                assistant_message["tool_calls"] = message["tool_calls"]
            messages.append(assistant_message)
            if not tool_calls:
                if successful_query_count == 0:
                    raise PlanningError(
                        "planner must successfully query the database before proposing"
                    )
                break
            if not isinstance(tool_calls, list):
                raise PlanningError("planner returned malformed tool calls")
            for tool_call in tool_calls:
                tool_call_count += 1
                if tool_call_count > DScheduler.MAX_INVESTIGATION_TOOL_CALLS:
                    raise PlanningError("planner exceeded the database tool-call limit")
                call_id, name, arguments = self._parse_tool_call(tool_call)
                if name == "query_experiment_database" and not schema_discovered:
                    result = {
                        "error": (
                            "Discover the database schema before issuing SQL so "
                            "table and column names are evidence-based."
                        )
                    }
                else:
                    try:
                        result = await execute_tool(name, arguments)
                    except ExperimentClientError as error:
                        result = {"error": str(error)}
                if name == "get_database_schema" and "error" not in result:
                    schema_discovered = True
                if name == "query_experiment_database" and "error" not in result:
                    successful_query_count += 1
                evidence.append(
                    {"tool": name, "arguments": arguments, "result": result}
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": json.dumps(result, separators=(",", ":")),
                    }
                )
        else:
            raise PlanningError("planner did not complete its database investigation")

        messages.append(
            {
                "role": "user",
                "content": (
                    "Using the evidence you queried, return the next experiment "
                    "proposal as the required JSON object."
                ),
            }
        )
        message = await self._request_message(
            messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "experiment_proposal",
                    "strict": True,
                    "schema": DScheduler.PROPOSAL_SCHEMA,
                },
            },
        )
        choice: Any = None
        try:
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
        return PlanningDecision(
            ExperimentProposal.from_dict(proposal_data, config),
            evidence,
        )

    async def _request_message(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": DScheduler.MAX_COMPLETION_TOKENS,
            "chat_template_kwargs": {"enable_thinking": False},
            "stream": False,
        }
        if tools is not None:
            request["tools"] = tools
            request["tool_choice"] = "auto"
        if response_format is not None:
            request["response_format"] = response_format
        response = await self.client.post(self.url, json=request)
        response.raise_for_status()
        try:
            message = response.json()["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise PlanningError("inference service returned a malformed message") from error
        if not isinstance(message, dict):
            raise PlanningError("inference service returned a malformed message")
        return message

    @staticmethod
    def _parse_tool_call(
        tool_call: dict[str, Any],
    ) -> tuple[str, str, dict[str, Any]]:
        try:
            call_id = tool_call["id"]
            function = tool_call["function"]
            name = function["name"]
            raw_arguments = function.get("arguments", "{}")
            arguments = json.loads(raw_arguments)
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise PlanningError("planner returned a malformed database tool call") from error
        if not isinstance(call_id, str) or not isinstance(name, str):
            raise PlanningError("planner returned a malformed database tool call")
        if not isinstance(arguments, dict):
            raise PlanningError("database tool arguments must be an object")
        if name not in {"get_database_schema", "query_experiment_database"}:
            raise PlanningError(f"unsupported planner tool: {name}")
        return call_id, name, arguments


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
        LOGGER.info("asking planner to investigate experiment data")
        decision = await self.planner.propose(config, self._execute_database_tool)
        proposal = decision.proposal
        proposal_data = asdict(proposal)
        plan_id = await asyncio.to_thread(
            self.plans.create,
            proposal_data,
            decision.evidence,
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

    async def _execute_database_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        if name == "get_database_schema":
            if arguments:
                raise PlanningError("get_database_schema does not accept arguments")
            return await self._request(MessageType.GET_DATABASE_SCHEMA)
        if name == "query_experiment_database":
            unknown = set(arguments) - {"sql", "parameters", "max_rows"}
            if unknown:
                raise PlanningError(
                    f"unsupported query arguments: {', '.join(sorted(unknown))}"
                )
            return await self._request(MessageType.EXECUTE_READ_QUERY, arguments)
        raise PlanningError(f"unsupported planner tool: {name}")

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
