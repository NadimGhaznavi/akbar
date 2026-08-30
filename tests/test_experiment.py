from __future__ import annotations

import asyncio
import socket
import unittest
from typing import Any

import zmq
import zmq.asyncio

from experiment.ExperimentClient import ExperimentClient, ExperimentClientError
from experiment.ExperimentConfig import ExperimentConfig
from experiment.ExperimentProtocol import MessageType
from experiment.ExperimentServer import ExperimentServer


class MemoryRepository:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}

    def initialize(self) -> None:
        pass

    def mark_interrupted(self) -> None:
        pass

    def create(self, experiment_id: str, config: dict[str, Any]) -> None:
        self.records[experiment_id] = {
            "experiment_id": experiment_id,
            "status": "queued",
            "config": config,
            "result": None,
            "error": None,
        }

    def mark_running(self, experiment_id: str) -> None:
        self.records[experiment_id]["status"] = "running"

    def finish(
        self,
        experiment_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        self.records[experiment_id].update(
            status=status,
            result=result,
            error=error,
        )

    def get(self, experiment_id: str) -> dict[str, Any] | None:
        return self.records.get(experiment_id)

    def count(self) -> int:
        return len(self.records)

    def resolve_suffix(self, suffix: str) -> list[str]:
        return [
            experiment_id
            for experiment_id in reversed(self.records)
            if experiment_id.endswith(suffix)
        ][:2]


def unused_tcp_endpoint() -> str:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    return f"tcp://127.0.0.1:{port}"


class ExperimentServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repository = MemoryRepository()
        self.control_endpoint = unused_tcp_endpoint()
        self.telemetry_endpoint = unused_tcp_endpoint()
        self.server = ExperimentServer(
            self.repository,
            control_endpoint=self.control_endpoint,
            telemetry_endpoint=self.telemetry_endpoint,
            default_config=ExperimentConfig(
                epochs=3,
                seed=7,
                board_size=8,
                max_moves_multiplier=10,
                replay_capacity=100,
                batch_size=8,
            ),
        )
        self.server_task = asyncio.create_task(self.server.run())
        self.client = ExperimentClient(self.control_endpoint, timeout_ms=1000)
        await asyncio.sleep(0.05)

    async def asyncTearDown(self) -> None:
        self.server.stop()
        await self.server_task

    async def request(self, message_type: MessageType, **kwargs) -> dict[str, Any]:
        return await asyncio.to_thread(self.client.request, message_type, **kwargs)

    async def test_complete_experiment_control_flow(self) -> None:
        pong = await self.request(MessageType.PING)
        self.assertEqual(pong["service"], "akbar-experimentd")

        subscriber = zmq.asyncio.Context.instance().socket(zmq.SUB)
        subscriber.setsockopt(zmq.LINGER, 0)
        subscriber.setsockopt(zmq.SUBSCRIBE, b"experiment.")
        subscriber.connect(self.telemetry_endpoint)
        await asyncio.sleep(0.05)

        accepted = await self.request(
            MessageType.START_EXPERIMENT,
        )
        experiment_id = accepted["experiment_id"]

        for _ in range(20):
            status = await self.request(
                MessageType.GET_EXPERIMENT_STATUS,
                experiment_id=experiment_id,
            )
            if status["status"] == "completed":
                break
            await asyncio.sleep(0.01)

        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["epoch"], 3)
        self.assertEqual(status["result"]["metrics"]["epochs_completed"], 3)
        result = await self.request(
            MessageType.GET_EXPERIMENT_RESULT,
            experiment_id=experiment_id,
        )
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["experiment_id"], experiment_id)
        self.assertEqual(result["configuration"], status["config"])
        self.assertEqual(result["metrics"]["epochs_completed"], 3)
        self.assertIn("elapsed_seconds", result["timing"])
        highscore = await self.request(
            MessageType.GET_CURRENT_HIGHSCORE,
            experiment_id=experiment_id,
        )
        self.assertEqual(highscore["highscore"], status["highscore"])
        self.assertEqual(self.repository.records[experiment_id]["status"], "completed")
        telemetry = []
        try:
            for _ in range(3):
                topic, payload = await asyncio.wait_for(
                    subscriber.recv_multipart(), timeout=1
                )
                self.assertEqual(
                    topic,
                    f"experiment.{experiment_id}.epoch".encode(),
                )
                telemetry.append(payload)
        finally:
            subscriber.close()
        self.assertEqual(len(telemetry), 3)

    async def test_stop_active_experiment(self) -> None:
        self.server.default_config = ExperimentConfig(
            epochs=1_000,
            seed=7,
            board_size=8,
            max_moves_multiplier=10,
            replay_capacity=100,
            batch_size=8,
        )
        accepted = await self.request(
            MessageType.START_EXPERIMENT,
        )
        experiment_id = accepted["experiment_id"]
        await self.request(
            MessageType.STOP_EXPERIMENT,
            experiment_id=experiment_id,
        )

        for _ in range(20):
            status = await self.request(
                MessageType.GET_EXPERIMENT_STATUS,
                experiment_id=experiment_id,
            )
            if status["status"] == "cancelled":
                break
            await asyncio.sleep(0.01)
        self.assertEqual(status["status"], "cancelled")

    async def test_start_rejects_runtime_configuration(self) -> None:
        with self.assertRaisesRegex(
            ExperimentClientError,
            "does not accept configuration",
        ):
            await self.request(
                MessageType.START_EXPERIMENT,
                payload={"epochs": 1},
            )

    async def test_experiment_count_uses_persisted_records(self) -> None:
        initial = await self.request(MessageType.GET_EXPERIMENT_COUNT)
        self.assertEqual(initial["experiment_count"], 0)
        await self.request(MessageType.START_EXPERIMENT)
        counted = await self.request(MessageType.GET_EXPERIMENT_COUNT)
        self.assertEqual(counted["experiment_count"], 1)

    async def test_resolve_experiment_id_suffix(self) -> None:
        accepted = await self.request(MessageType.START_EXPERIMENT)
        experiment_id = accepted["experiment_id"]
        resolved = await self.request(
            MessageType.RESOLVE_EXPERIMENT_ID,
            payload={"suffix": experiment_id[-4:]},
        )
        self.assertEqual(resolved["experiment_id"], experiment_id)


if __name__ == "__main__":
    unittest.main()
