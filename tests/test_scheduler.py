from __future__ import annotations

import asyncio
import unittest
from typing import Any

from constants.DScheduler import DScheduler
from experiment.ExperimentProtocol import MessageType
from scheduler.SchedulerServer import (
    ExperimentProposal,
    LlamaPlanner,
    PlanningError,
    Scheduler,
)


class FakeHTTPResponse:
    def __init__(self, content: Any) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return {"choices": [{"message": {"content": self.content}}]}


class FakeHTTPClient:
    def __init__(
        self,
        content: Any = (
            '{"epochs":50,"learning_rate":0.0008,'
            '"rationale":"Compare the previous run."}'
        ),
    ) -> None:
        self.content = content
        self.requests: list[tuple[str, dict[str, Any]]] = []

    async def post(self, url: str, json: dict[str, Any]) -> FakeHTTPResponse:
        self.requests.append((url, json))
        return FakeHTTPResponse(self.content)

    async def aclose(self) -> None:
        pass


class FakeExperimentControl:
    def __init__(self, status: str = "completed") -> None:
        self.status = status
        self.calls: list[tuple[MessageType, dict[str, Any] | None]] = []

    def request(
        self,
        message_type: MessageType,
        payload: dict[str, Any] | None = None,
        experiment_id: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append((message_type, payload))
        if message_type is MessageType.GET_EXPERIMENT_STATUS:
            return {"status": self.status}
        if message_type is MessageType.GET_EXPERIMENT_CONFIG:
            return {
                "epochs": 50,
                "learning_rate": 0.001,
                "limits": {
                    "epochs": {"minimum": 50, "maximum": 100_000},
                    "learning_rate": {"minimum": 0.000_001, "maximum": 0.1},
                },
            }
        if message_type is MessageType.LIST_EXPERIMENT_RESULTS:
            return {
                "results": [
                    {
                        "experiment_id": "experiment-1",
                        "epochs": 50,
                        "learning_rate": 0.001,
                        "highscore": 2,
                        "average_score": 0.08,
                    }
                ],
                "returned": 1,
            }
        if message_type is MessageType.SET_EXPERIMENT_CONFIG:
            return dict(payload or {})
        if message_type is MessageType.START_EXPERIMENT:
            return {"experiment_id": "experiment-2", "status": "queued"}
        raise AssertionError(f"unexpected request: {message_type}")


class FakePlanner:
    def __init__(self) -> None:
        self.inputs: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []

    async def propose(
        self,
        config: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> ExperimentProposal:
        self.inputs.append((config, results))
        return ExperimentProposal(
            epochs=50,
            learning_rate=0.0008,
            rationale="Test a lower rate after reviewing experiment-1.",
        )


class MemoryPlanningRepository:
    def __init__(self) -> None:
        self.proposals: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
        self.started: list[tuple[str, str]] = []
        self.failed: list[tuple[str, str]] = []

    def initialize(self) -> None:
        pass

    def create(
        self,
        proposal: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> str:
        self.proposals.append((proposal, evidence))
        return "plan-1"

    def mark_started(self, plan_id: str, experiment_id: str) -> None:
        self.started.append((plan_id, experiment_id))

    def mark_failed(self, plan_id: str, error: str) -> None:
        self.failed.append((plan_id, error))


class SchedulerTest(unittest.TestCase):
    def test_planner_makes_one_structured_request_with_previous_results(self) -> None:
        http = FakeHTTPClient()
        planner = LlamaPlanner(client=http)
        config = FakeExperimentControl().request(MessageType.GET_EXPERIMENT_CONFIG)
        results = [{"experiment_id": "experiment-1", "highscore": 2}]

        proposal = asyncio.run(planner.propose(config, results))

        self.assertEqual(proposal.learning_rate, 0.0008)
        self.assertEqual(len(http.requests), 1)
        request = http.requests[0][1]
        self.assertEqual(request["response_format"]["type"], "json_schema")
        self.assertIn("previous_experiments", request["messages"][1]["content"])

    def test_planner_accepts_fenced_json_from_llama(self) -> None:
        http = FakeHTTPClient(
            """```json
{"epochs":50,"learning_rate":0.0008,"rationale":"Try a lower rate."}
```"""
        )
        planner = LlamaPlanner(client=http)
        config = FakeExperimentControl().request(MessageType.GET_EXPERIMENT_CONFIG)

        proposal = asyncio.run(planner.propose(config, []))

        self.assertEqual(proposal.rationale, "Try a lower rate.")

    def test_idle_cycle_reviews_history_and_starts_one_experiment(self) -> None:
        experiment = FakeExperimentControl()
        planner = FakePlanner()
        plans = MemoryPlanningRepository()
        scheduler = Scheduler(experiment, planner, plans)

        experiment_id = asyncio.run(scheduler.run_once())

        self.assertEqual(experiment_id, "experiment-2")
        self.assertEqual(len(planner.inputs), 1)
        self.assertEqual(planner.inputs[0][1][0]["experiment_id"], "experiment-1")
        self.assertEqual(
            experiment.calls,
            [
                (MessageType.GET_EXPERIMENT_STATUS, None),
                (MessageType.GET_EXPERIMENT_CONFIG, None),
                (
                    MessageType.LIST_EXPERIMENT_RESULTS,
                    {"limit": DScheduler.RESULT_HISTORY_LIMIT},
                ),
                (
                    MessageType.SET_EXPERIMENT_CONFIG,
                    {"epochs": 50, "learning_rate": 0.0008},
                ),
                (MessageType.START_EXPERIMENT, None),
            ],
        )
        self.assertEqual(plans.started, [("plan-1", "experiment-2")])
        self.assertIn("rationale", plans.proposals[0][0])

    def test_active_experiment_skips_planning(self) -> None:
        experiment = FakeExperimentControl(status="running")
        planner = FakePlanner()
        plans = MemoryPlanningRepository()

        result = asyncio.run(Scheduler(experiment, planner, plans).run_once())

        self.assertIsNone(result)
        self.assertEqual(planner.inputs, [])
        self.assertEqual(
            experiment.calls,
            [(MessageType.GET_EXPERIMENT_STATUS, None)],
        )

    def test_scheduler_rejects_unsafe_timing_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "interval must be positive"):
            Scheduler(
                FakeExperimentControl(),
                FakePlanner(),
                MemoryPlanningRepository(),
                interval_seconds=0,
            )

    def test_proposal_validation_enforces_config_limits(self) -> None:
        config = FakeExperimentControl().request(MessageType.GET_EXPERIMENT_CONFIG)
        with self.assertRaisesRegex(PlanningError, "epochs are outside"):
            ExperimentProposal.from_dict(
                {
                    "epochs": 49,
                    "learning_rate": 0.001,
                    "rationale": "Too short.",
                },
                config,
            )

    def test_default_schedule_checks_every_fifteen_seconds(self) -> None:
        self.assertEqual(DScheduler.INITIAL_DELAY_SECONDS, 15)
        self.assertEqual(DScheduler.INTERVAL_SECONDS, 15)


if __name__ == "__main__":
    unittest.main()
