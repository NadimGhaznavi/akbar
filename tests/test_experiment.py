from __future__ import annotations

import asyncio
import socket
import unittest
from typing import Any

from experiment.ExperimentClient import ExperimentClient, ExperimentClientError
from experiment.ExperimentConfig import ExperimentConfig
from experiment.ExperimentDesign import build_simulation_configs
from experiment.ExperimentProtocol import MessageType
from experiment.ExperimentRepository import validate_read_query
from experiment.ExperimentServer import ExperimentServer


class MemoryRepository:
    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.simulations: dict[str, dict[str, Any]] = {}
        self.config: dict[str, Any] | None = None

    def initialize(self) -> None: pass
    def mark_interrupted(self) -> None: pass
    def load_config(self) -> dict[str, Any] | None: return self.config
    def save_config(self, config: dict[str, Any]) -> None: self.config = dict(config)

    def create(self, experiment_id: str, config: dict[str, Any]) -> None:
        self.records[experiment_id] = {
            "experiment_id": experiment_id, "status": "queued", "config": config,
            "result": None, "error": None,
        }

    def mark_running(self, experiment_id: str) -> None:
        self.records[experiment_id]["status"] = "running"

    def finish(self, experiment_id: str, status: str, result=None, error=None) -> None:
        self.records[experiment_id].update(status=status, result=result, error=error)

    def get(self, experiment_id: str) -> dict[str, Any] | None:
        return self.records.get(experiment_id)

    def count(self) -> int: return len(self.records)
    def resolve_suffix(self, suffix: str) -> list[str]:
        return [item for item in reversed(self.records) if item.endswith(suffix)][:2]

    def create_simulation(self, simulation_id, experiment_id, config) -> None:
        self.simulations[simulation_id] = {
            "simulation_id": simulation_id, "experiment_id": experiment_id,
            "status": "running", "config": config, "result": None,
        }

    def finish_simulation(self, simulation_id, status, result=None, error=None) -> None:
        self.simulations[simulation_id].update(status=status, result=result, error=error)

    def schema(self) -> list[dict[str, Any]]:
        return [{"table_name": "simulation_runs", "column_name": "seed",
                 "data_type": "bigint", "is_nullable": "NO", "column_key": ""}]

    def execute_read_query(self, sql, parameters, max_rows) -> dict[str, Any]:
        rows = list(self.simulations.values())[:max_rows]
        return {"columns": ["simulation_id"], "rows": rows,
                "returned": len(rows), "truncated": False}


class FakeRunner:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    async def run(self, stop_event, publish_telemetry) -> dict[str, Any]:
        await asyncio.sleep(0)
        if stop_event.is_set():
            from experiment.ExperimentRunner import ExperimentCancelled
            raise ExperimentCancelled
        await publish_telemetry({"epoch": self.config.epochs, "score": 1,
                                 "highscore": 2, "progress": 1.0})
        return {"epochs": self.config.epochs, "highscore": 2,
                "average_score": 1.0, "average_loss": 0.5,
                "total_moves": 10, "replay_size": 5, "elapsed_seconds": 0.01}


def unused_tcp_endpoint() -> str:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return f"tcp://127.0.0.1:{candidate.getsockname()[1]}"


class ExperimentServiceTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repository = MemoryRepository()
        self.server = ExperimentServer(
            self.repository,
            control_endpoint=unused_tcp_endpoint(),
            telemetry_endpoint=unused_tcp_endpoint(),
            default_config=ExperimentConfig(board_size=8, replay_capacity=100,
                                            batch_size=8, epsilon_start=0.9),
            runner_factory=FakeRunner,
        )
        self.server_task = asyncio.create_task(self.server.run())
        self.client = ExperimentClient(self.server.control_endpoint, timeout_ms=2000)
        await asyncio.sleep(0.05)

    async def asyncTearDown(self) -> None:
        self.server.stop()
        await self.server_task

    async def request(self, message_type: MessageType, **kwargs) -> dict[str, Any]:
        return await asyncio.to_thread(self.client.request, message_type, **kwargs)

    async def test_batch_persists_135_separate_simulation_results(self) -> None:
        accepted = await self.request(
            MessageType.START_EXPERIMENT,
            payload={"learning_rate": 0.001, "epsilon_start": 0.9,
                     "epsilon_decay": 0.995},
        )
        experiment_id = accepted["experiment_id"]
        for _ in range(200):
            status = await self.request(MessageType.GET_EXPERIMENT_STATUS,
                                        experiment_id=experiment_id)
            if status["status"] == "completed": break
            await asyncio.sleep(0.01)
        self.assertEqual(status["status"], "completed")
        self.assertEqual(len(self.repository.simulations), 135)
        self.assertTrue(all(row["result"] for row in self.repository.simulations.values()))
        self.assertIsNone(self.repository.records[experiment_id]["result"])
        methodology = self.repository.records[experiment_id]["config"]["methodology"]
        self.assertEqual(methodology["simulation_count"], 135)
        self.assertEqual(methodology["seeds"], [1970, 1971, 1972, 1973, 1974])

    async def test_schema_and_open_ended_query_api(self) -> None:
        schema = await self.request(MessageType.GET_DATABASE_SCHEMA)
        self.assertIn("simulation_runs", schema["tables"])
        result = await self.request(
            MessageType.EXECUTE_READ_QUERY,
            payload={"sql": "SELECT * FROM simulation_runs", "max_rows": 12},
        )
        self.assertEqual(result["returned"], 0)

    async def test_rejects_epoch_override(self) -> None:
        with self.assertRaisesRegex(ExperimentClientError, "unsupported"):
            await self.request(MessageType.START_EXPERIMENT, payload={"epochs": 1})


class ExperimentDesignTest(unittest.TestCase):
    def test_design_has_27_configurations_across_five_fixed_seeds(self) -> None:
        configs = build_simulation_configs(ExperimentConfig(epsilon_start=0.9))
        combinations = {(item.learning_rate, item.epsilon_start,
                         item.epsilon_decay) for item in configs}
        self.assertEqual(len(configs), 135)
        self.assertEqual(len(combinations), 27)
        self.assertEqual({item.seed for item in configs}, {1970, 1971, 1972, 1973, 1974})
        self.assertEqual({item.epochs for item in configs}, {1500})

    def test_read_query_validation_rejects_writes_and_filesystem_access(self) -> None:
        self.assertEqual(validate_read_query("SELECT * FROM simulation_runs"),
                         "SELECT * FROM simulation_runs")
        self.assertTrue(validate_read_query(
            "WITH recent AS (SELECT * FROM simulation_runs) SELECT * FROM recent"
        ))
        for sql in (
            "DELETE FROM simulation_runs",
            "SELECT 1; DELETE FROM simulation_runs",
            "SELECT * INTO OUTFILE '/tmp/results' FROM simulation_runs",
            "SELECT LOAD_FILE('/etc/passwd')",
        ):
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                validate_read_query(sql)


if __name__ == "__main__":
    unittest.main()
