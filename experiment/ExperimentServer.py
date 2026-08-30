#!/usr/bin/env python3
"""Akbar experiment control and telemetry service."""

from __future__ import annotations

import asyncio
import logging
import signal
from dataclasses import replace
from typing import Any
from uuid import uuid4

import zmq
import zmq.asyncio

from constants.DAkbar import DAkbar
from constants.DExperiment import DExperiment
from experiment.ExperimentConfig import ExperimentConfig
from experiment.ExperimentProtocol import (
    ExperimentMessage,
    ExperimentStatus,
    MessageType,
    ProtocolError,
)
from experiment.ExperimentRepository import (
    ExperimentRepository,
    MariaDBExperimentRepository,
)
from experiment.ExperimentRunner import ExperimentCancelled, ExperimentRunner
from experiment.ExperimentState import ExperimentState, ExperimentStateStore, utc_now

LOG = logging.getLogger("akbar.experimentd")


class ExperimentServer:
    """Own one experiment runner and expose its control plane over ZMQ."""

    def __init__(
        self,
        repository: ExperimentRepository,
        control_endpoint: str = DExperiment.CONTROL_ENDPOINT,
        telemetry_endpoint: str = DExperiment.TELEMETRY_ENDPOINT,
        default_config: ExperimentConfig | None = None,
    ) -> None:
        self.repository = repository
        self.control_endpoint = control_endpoint
        self.telemetry_endpoint = telemetry_endpoint
        self.default_config = default_config or ExperimentConfig()
        self.state = ExperimentStateStore()
        self._context = zmq.asyncio.Context.instance()
        self._control = self._context.socket(zmq.ROUTER)
        self._telemetry = self._context.socket(zmq.PUB)
        self._runner_task: asyncio.Task[None] | None = None
        self._runner_stop = asyncio.Event()
        self._shutdown = asyncio.Event()

    async def run(self) -> None:
        """Initialize persistence, bind sockets, and serve until stopped."""
        await asyncio.to_thread(self.repository.initialize)
        await asyncio.to_thread(self.repository.mark_interrupted)
        persisted_config = await asyncio.to_thread(self.repository.load_config)
        if persisted_config is None:
            await asyncio.to_thread(
                self.repository.save_config,
                self.default_config.to_dict(),
            )
        else:
            normalized_config = dict(persisted_config)
            normalized_config["epochs"] = max(
                DExperiment.MIN_EPOCHS,
                normalized_config["epochs"],
            )
            self.default_config = ExperimentConfig(**normalized_config)
            if normalized_config != persisted_config:
                await asyncio.to_thread(
                    self.repository.save_config,
                    self.default_config.to_dict(),
                )
        self._control.setsockopt(zmq.LINGER, 0)
        self._telemetry.setsockopt(zmq.LINGER, 0)
        self._telemetry.setsockopt(
            zmq.SNDHWM,
            DExperiment.TELEMETRY_HIGH_WATER_MARK,
        )
        self._control.bind(self.control_endpoint)
        self._telemetry.bind(self.telemetry_endpoint)
        LOG.info(
            "Experiment service listening on %s; telemetry on %s",
            self.control_endpoint,
            self.telemetry_endpoint,
        )
        try:
            await self._control_loop()
        finally:
            self._runner_stop.set()
            if self._runner_task is not None:
                await self._runner_task
            self._control.close()
            self._telemetry.close()

    def stop(self) -> None:
        self._shutdown.set()

    async def _control_loop(self) -> None:
        poller = zmq.asyncio.Poller()
        poller.register(self._control, zmq.POLLIN)
        while not self._shutdown.is_set():
            events = dict(await poller.poll(timeout=250))
            if self._control not in events:
                continue
            frames = await self._control.recv_multipart()
            if len(frames) < 2:
                LOG.warning("Discarding malformed ROUTER message")
                continue
            reply = await self._handle_message(frames[-1])
            await self._control.send_multipart([*frames[:-1], reply.to_json()])

    async def _handle_message(self, raw_message: bytes) -> ExperimentMessage:
        request: ExperimentMessage | None = None
        try:
            request = ExperimentMessage.from_json(raw_message)
            return await self._dispatch(request)
        except (ProtocolError, ValueError, TypeError) as error:
            LOG.info("Rejected control request: %s", error)
            if request is not None:
                return request.reply(MessageType.ERROR, {"error": str(error)})
            return ExperimentMessage(MessageType.ERROR, {"error": str(error)})
        except Exception as error:
            LOG.exception("Control request failed")
            if request is not None:
                return request.reply(MessageType.ERROR, {"error": str(error)})
            return ExperimentMessage(MessageType.ERROR, {"error": str(error)})

    async def _dispatch(self, request: ExperimentMessage) -> ExperimentMessage:
        if request.message_type is MessageType.PING:
            return request.reply(
                MessageType.PONG,
                {"service": "akbar-experimentd", "version": DAkbar.VERSION},
            )
        if request.message_type is MessageType.START_EXPERIMENT:
            return await self._start(request)
        if request.message_type is MessageType.GET_EXPERIMENT_STATUS:
            return await self._status(request)
        if request.message_type is MessageType.GET_EXPERIMENT_RESULT:
            return await self._result(request)
        if request.message_type is MessageType.GET_EXPERIMENT_COUNT:
            return await self._count(request)
        if request.message_type is MessageType.RESOLVE_EXPERIMENT_ID:
            return await self._resolve_experiment_id(request)
        if request.message_type is MessageType.GET_EXPERIMENT_CONFIG:
            return request.reply(
                MessageType.EXPERIMENT_CONFIG,
                self._config_payload(),
            )
        if request.message_type is MessageType.SET_EXPERIMENT_CONFIG:
            return await self._set_config(request)
        if request.message_type is MessageType.LIST_EXPERIMENT_RESULTS:
            return await self._list_results(request)
        if request.message_type is MessageType.GET_CURRENT_HIGHSCORE:
            return self._highscore(request)
        if request.message_type is MessageType.STOP_EXPERIMENT:
            return self._stop_experiment(request)
        raise ProtocolError(f"unsupported request type: {request.message_type.value}")

    async def _start(self, request: ExperimentMessage) -> ExperimentMessage:
        if self._runner_task is not None and not self._runner_task.done():
            raise ProtocolError("an experiment is already running")
        if request.payload:
            raise ProtocolError("start_experiment does not accept configuration")
        seed = await asyncio.to_thread(self.repository.allocate_seed)
        config = replace(self.default_config, seed=seed)
        experiment_id = str(uuid4())
        config_data = config.to_dict()
        await asyncio.to_thread(self.repository.create, experiment_id, config_data)
        self.state.create(experiment_id, config_data)
        self._runner_stop = asyncio.Event()
        self._runner_task = asyncio.create_task(
            self._run_experiment(experiment_id, config),
            name=f"experiment-{experiment_id}",
        )
        return request.reply(
            MessageType.EXPERIMENT_ACCEPTED,
            {"status": ExperimentStatus.QUEUED.value, "config": config_data},
            experiment_id,
        )

    async def _set_config(self, request: ExperimentMessage) -> ExperimentMessage:
        if self._runner_task is not None and not self._runner_task.done():
            raise ProtocolError("configuration cannot change during an experiment")
        if not request.payload:
            raise ProtocolError("at least one configuration value is required")
        unknown = set(request.payload) - {"epochs", "learning_rate"}
        if unknown:
            raise ProtocolError(
                f"unsupported configuration fields: {', '.join(sorted(unknown))}"
            )
        updated = replace(self.default_config, **request.payload)
        await asyncio.to_thread(
            self.repository.save_config,
            updated.to_dict(),
        )
        self.default_config = updated
        return request.reply(
            MessageType.EXPERIMENT_CONFIG_UPDATED,
            self._config_payload(),
        )

    def _config_payload(self) -> dict[str, Any]:
        return {
            "epochs": self.default_config.epochs,
            "learning_rate": self.default_config.learning_rate,
            "limits": {
                "epochs": {
                    "minimum": DExperiment.MIN_EPOCHS,
                    "maximum": DExperiment.MAX_EPOCHS,
                },
                "learning_rate": {
                    "minimum": DExperiment.MIN_LEARNING_RATE,
                    "maximum": DExperiment.MAX_LEARNING_RATE,
                },
            },
        }

    async def _list_results(
        self,
        request: ExperimentMessage,
    ) -> ExperimentMessage:
        limit = request.payload.get(
            "limit",
            DExperiment.DEFAULT_RESULT_LIST_LIMIT,
        )
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ProtocolError("result list limit must be an integer")
        if not 1 <= limit <= DExperiment.MAX_RESULT_LIST_LIMIT:
            raise ProtocolError(
                "result list limit must be between 1 and "
                f"{DExperiment.MAX_RESULT_LIST_LIMIT}"
            )
        results = await asyncio.to_thread(self.repository.list_results, limit)
        return request.reply(
            MessageType.EXPERIMENT_RESULTS,
            {"results": results, "returned": len(results)},
        )

    async def _run_experiment(
        self, experiment_id: str, config: ExperimentConfig
    ) -> None:
        state = self.state.get(experiment_id)
        if state is None:
            return
        try:
            # Persistence is deliberately outside the epoch loop.
            await asyncio.to_thread(self.repository.mark_running, experiment_id)
            state.status = ExperimentStatus.RUNNING
            state.started_at = utc_now()
            runner_result = await ExperimentRunner(config).run(
                self._runner_stop,
                lambda telemetry: self._publish_telemetry(state, telemetry),
            )
            state.status = ExperimentStatus.COMPLETED
            state.completed_at = utc_now()
            result = {
                "schema_version": 1,
                "experiment_id": experiment_id,
                "status": state.status.value,
                "configuration": state.config,
                "metrics": {
                    "epochs_completed": runner_result["epochs"],
                    "highscore": runner_result["highscore"],
                    "average_score": runner_result["average_score"],
                    "average_loss": runner_result["average_loss"],
                    "total_moves": runner_result["total_moves"],
                    "replay_size": runner_result["replay_size"],
                },
                "timing": {
                    "started_at": state.started_at,
                    "completed_at": state.completed_at,
                    "elapsed_seconds": runner_result["elapsed_seconds"],
                },
            }
            state.result = result
            await asyncio.to_thread(
                self.repository.finish,
                experiment_id,
                state.status.value,
                result,
                None,
            )
        except ExperimentCancelled:
            state.status = ExperimentStatus.CANCELLED
            state.completed_at = utc_now()
            await asyncio.to_thread(
                self.repository.finish,
                experiment_id,
                state.status.value,
                None,
                "Experiment stopped by request",
            )
        except Exception as error:
            LOG.exception("Experiment %s failed", experiment_id)
            state.status = ExperimentStatus.FAILED
            state.error = str(error)
            state.completed_at = utc_now()
            await asyncio.to_thread(
                self.repository.finish,
                experiment_id,
                state.status.value,
                None,
                state.error,
            )

    async def _publish_telemetry(
        self, state: ExperimentState, telemetry: dict[str, Any]
    ) -> None:
        state.epoch = telemetry["epoch"]
        state.score = telemetry["score"]
        state.highscore = telemetry["highscore"]
        state.progress = telemetry["progress"]
        message = ExperimentMessage(
            MessageType.TELEMETRY,
            telemetry,
            experiment_id=state.experiment_id,
        )
        topic = f"experiment.{state.experiment_id}.epoch".encode()
        try:
            await self._telemetry.send_multipart(
                [topic, message.to_json()], flags=zmq.DONTWAIT
            )
        except zmq.Again:
            LOG.warning("Dropping telemetry because the PUB queue is full")

    async def _status(self, request: ExperimentMessage) -> ExperimentMessage:
        state = self.state.get(request.experiment_id)
        if state is not None:
            data = state.to_dict()
        elif request.experiment_id:
            data = await asyncio.to_thread(self.repository.get, request.experiment_id)
            if data is None:
                raise ProtocolError("experiment not found")
        else:
            return request.reply(
                MessageType.EXPERIMENT_STATUS,
                {"status": ExperimentStatus.READY.value},
            )
        return request.reply(
            MessageType.EXPERIMENT_STATUS,
            data,
            data["experiment_id"],
        )

    async def _result(self, request: ExperimentMessage) -> ExperimentMessage:
        if not request.experiment_id:
            raise ProtocolError("experiment_id is required")
        state = self.state.get(request.experiment_id)
        if state is not None:
            if state.status is not ExperimentStatus.COMPLETED or state.result is None:
                raise ProtocolError("experiment result is not available")
            result = state.result
        else:
            record = await asyncio.to_thread(
                self.repository.get,
                request.experiment_id,
            )
            if record is None:
                raise ProtocolError("experiment not found")
            result = record["result"]
            if record["status"] != ExperimentStatus.COMPLETED.value or result is None:
                raise ProtocolError("experiment result is not available")
        return request.reply(
            MessageType.EXPERIMENT_RESULT,
            result,
            request.experiment_id,
        )

    async def _count(self, request: ExperimentMessage) -> ExperimentMessage:
        count = await asyncio.to_thread(self.repository.count)
        return request.reply(
            MessageType.EXPERIMENT_COUNT,
            {"experiment_count": count},
        )

    async def _resolve_experiment_id(
        self,
        request: ExperimentMessage,
    ) -> ExperimentMessage:
        suffix = request.payload.get("suffix")
        if not isinstance(suffix, str) or len(suffix) != 4:
            raise ProtocolError("experiment ID suffix must contain exactly 4 characters")
        if not all(character in "0123456789abcdefABCDEF" for character in suffix):
            raise ProtocolError("experiment ID suffix must be hexadecimal")
        matches = await asyncio.to_thread(
            self.repository.resolve_suffix,
            suffix.lower(),
        )
        if not matches:
            raise ProtocolError("experiment not found")
        if len(matches) > 1:
            raise ProtocolError("experiment ID suffix is ambiguous")
        return request.reply(
            MessageType.EXPERIMENT_ID_RESOLVED,
            {},
            matches[0],
        )

    def _highscore(self, request: ExperimentMessage) -> ExperimentMessage:
        state = self.state.get(request.experiment_id)
        if state is None:
            raise ProtocolError("no matching live experiment is available")
        return request.reply(
            MessageType.CURRENT_HIGHSCORE,
            {
                "status": state.status.value,
                "epoch": state.epoch,
                "highscore": state.highscore,
            },
            state.experiment_id,
        )

    def _stop_experiment(self, request: ExperimentMessage) -> ExperimentMessage:
        state = self.state.get(request.experiment_id)
        if state is None:
            raise ProtocolError("no matching live experiment is available")
        if self._runner_task is None or self._runner_task.done():
            raise ProtocolError("the experiment is not running")
        self._runner_stop.set()
        return request.reply(
            MessageType.STOP_REQUESTED,
            {"status": state.status.value},
            state.experiment_id,
        )


async def serve() -> None:
    server = ExperimentServer(MariaDBExperimentRepository())
    loop = asyncio.get_running_loop()
    for shutdown_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(shutdown_signal, server.stop)
    await server.run()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    asyncio.run(serve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
