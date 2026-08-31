from __future__ import annotations

import asyncio
import unittest
from typing import Any

from constants.DScheduler import DScheduler
from experiment.ExperimentClient import ExperimentClientError
from experiment.ExperimentProtocol import MessageType
from scheduler.SchedulerServer import (
    ExperimentProposal,
    LlamaPlanner,
    PlanningDecision,
    PlanningError,
    Scheduler,
)


class FakeHTTPResponse:
    def __init__(self, message: dict[str, Any]) -> None:
        self.message = message

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return {"choices": [{"message": self.message}]}


class FakeHTTPClient:
    def __init__(
        self,
        messages: list[dict[str, Any]] | None = None,
    ) -> None:
        self.messages = messages or [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-1", "type": "function",
                        "function": {
                            "name": "get_database_schema",
                            "arguments": "{}",
                        },
                    },
                    {
                        "id": "call-2", "type": "function",
                        "function": {
                            "name": "query_experiment_database",
                            "arguments": '{"sql":"SELECT COUNT(*) AS count FROM simulation_runs"}',
                        },
                    },
                ],
            },
            {"role": "assistant", "content": "Investigation complete."},
            {
                "role": "assistant",
                "content": (
                    '{"learning_rate":0.0008,"epsilon_start":0.9,'
                    '"epsilon_decay":0.995,'
                    '"rationale":"Compare the complete experiment."}'
                ),
            },
        ]
        self.requests: list[tuple[str, dict[str, Any]]] = []

    async def post(self, url: str, json: dict[str, Any]) -> FakeHTTPResponse:
        self.requests.append((url, json))
        return FakeHTTPResponse(self.messages.pop(0))

    async def aclose(self) -> None:
        pass


class FakeExperimentControl:
    def __init__(
        self,
        status: str = "completed",
        experiment_count: int = 1,
    ) -> None:
        self.status = status
        self.experiment_count = experiment_count
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
        if message_type is MessageType.GET_EXPERIMENT_COUNT:
            return {"experiment_count": self.experiment_count}
        if message_type is MessageType.GET_EXPERIMENT_CONFIG:
            return {
                "epochs": 50,
                "learning_rate": 0.001,
                "epsilon_start": 0.9,
                "epsilon_decay": 0.995,
                "limits": {
                    "learning_rate": {"minimum": 0.000_001, "maximum": 0.1},
                },
            }
        if message_type is MessageType.EXECUTE_READ_QUERY:
            return {
                "rows": [
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
        self.inputs: list[dict[str, Any]] = []

    async def propose(
        self,
        config: dict[str, Any],
        execute_tool,
    ) -> PlanningDecision:
        self.inputs.append(config)
        arguments = {"sql": "SELECT * FROM simulation_runs"}
        result = await execute_tool("query_experiment_database", arguments)
        return PlanningDecision(
            ExperimentProposal(
                learning_rate=0.0008,
                epsilon_start=0.9,
                epsilon_decay=0.995,
                rationale="Test a lower rate after reviewing experiment-1.",
            ),
            [{"tool": "query_experiment_database", "arguments": arguments,
              "result": result}],
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
    def test_planner_investigates_with_sql_before_structured_proposal(self) -> None:
        http = FakeHTTPClient()
        planner = LlamaPlanner(client=http)
        config = FakeExperimentControl().request(MessageType.GET_EXPERIMENT_CONFIG)
        calls = []

        async def execute_tool(name, arguments):
            calls.append((name, arguments))
            if name == "get_database_schema":
                return {"tables": {"simulation_runs": [], "experiments": []}}
            if "FROM experiments" in arguments["sql"]:
                return {"rows": [], "returned": 0}
            return {"rows": [{"count": 27}], "returned": 1}

        decision = asyncio.run(planner.propose(config, execute_tool))

        self.assertEqual(decision.proposal.learning_rate, 0.0008)
        self.assertEqual(len(decision.evidence), 3)
        self.assertEqual(calls[0][0], "get_database_schema")
        self.assertEqual(calls[1][0], "query_experiment_database")
        self.assertEqual(calls[2][0], "query_experiment_database")
        self.assertEqual(len(http.requests), 3)
        request = http.requests[0][1]
        self.assertIn("tools", request)
        self.assertEqual(
            {tool["function"]["name"] for tool in request["tools"]},
            {"doc_browser", "get_database_schema", "query_experiment_database"},
        )
        self.assertNotIn("response_format", request)
        self.assertEqual(
            http.requests[-1][1]["response_format"]["type"], "json_schema"
        )
        self.assertEqual(
            request["chat_template_kwargs"],
            {"enable_thinking": False},
        )
        self.assertNotIn("reasoning_budget", request)
        self.assertIn("active_configuration", request["messages"][1]["content"])

    def test_scheduler_exposes_only_aknet_pages_to_planner(self) -> None:
        scheduler = Scheduler(
            FakeExperimentControl(), FakePlanner(), MemoryPlanningRepository()
        )
        homepage = asyncio.run(scheduler._execute_planner_tool("doc_browser", {}))
        rejected = asyncio.run(
            scheduler._execute_planner_tool("doc_browser", {"url": "/../README"})
        )

        self.assertEqual(homepage["url"], "/")
        self.assertIn("/snake-lab/", homepage["content"])
        self.assertIn("error", rejected)

    def test_planner_rejects_empty_final_content(self) -> None:
        http = FakeHTTPClient([{"role": "assistant", "content": "No query needed."}])
        planner = LlamaPlanner(client=http)
        config = FakeExperimentControl().request(MessageType.GET_EXPERIMENT_CONFIG)

        async def execute_tool(_name, _arguments):
            return {}

        with self.assertRaisesRegex(PlanningError, "must successfully query"):
            asyncio.run(planner.propose(config, execute_tool))

    def test_planner_receives_sql_errors_and_can_correct_its_query(self) -> None:
        final_content = (
            '{"learning_rate":0.0008,"epsilon_start":0.9,'
            '"epsilon_decay":0.995,"rationale":"Used corrected SQL."}'
        )
        http = FakeHTTPClient([
            {"role": "assistant", "content": None, "tool_calls": [{
                "id": "schema", "type": "function", "function": {
                    "name": "get_database_schema", "arguments": "{}",
                },
            }]},
            {"role": "assistant", "content": None, "tool_calls": [{
                "id": "bad", "type": "function", "function": {
                    "name": "query_experiment_database",
                    "arguments": '{"sql":"SELECT * FROM missing"}',
                },
            }]},
            {"role": "assistant", "content": None, "tool_calls": [{
                "id": "good", "type": "function", "function": {
                    "name": "query_experiment_database",
                    "arguments": '{"sql":"SELECT * FROM simulation_runs"}',
                },
            }]},
            {"role": "assistant", "content": "Investigation complete."},
            {"role": "assistant", "content": final_content},
        ])
        planner = LlamaPlanner(client=http)
        config = FakeExperimentControl().request(MessageType.GET_EXPERIMENT_CONFIG)

        async def execute_tool(name, arguments):
            if name == "get_database_schema":
                return {"tables": {"simulation_runs": []}}
            if "missing" in arguments["sql"]:
                raise ExperimentClientError("Table 'missing' doesn't exist")
            if "FROM experiments" in arguments["sql"]:
                return {"rows": [], "returned": 0}
            return {"rows": [], "returned": 0}

        decision = asyncio.run(planner.propose(config, execute_tool))

        self.assertEqual(decision.proposal.rationale, "Used corrected SQL.")
        self.assertIn("error", decision.evidence[1]["result"])
        self.assertNotIn("error", decision.evidence[2]["result"])

    def test_round_limit_finalizes_when_investigation_has_successful_queries(self) -> None:
        tool_messages = []
        for index in range(DScheduler.MAX_INVESTIGATION_ROUNDS):
            name = "get_database_schema" if index == 0 else "query_experiment_database"
            arguments = "{}" if index == 0 else '{"sql":"SELECT 1 AS value"}'
            tool_messages.append({
                "role": "assistant", "content": None, "tool_calls": [{
                    "id": f"call-{index}", "type": "function", "function": {
                        "name": name, "arguments": arguments,
                    },
                }],
            })
        tool_messages.append({
            "role": "assistant",
            "content": (
                '{"learning_rate":0.0008,"epsilon_start":0.9,'
                '"epsilon_decay":0.995,"rationale":"Bounded evidence."}'
            ),
        })
        planner = LlamaPlanner(client=FakeHTTPClient(tool_messages))
        config = FakeExperimentControl().request(MessageType.GET_EXPERIMENT_CONFIG)

        async def execute_tool(name, arguments):
            if name == "get_database_schema":
                return {"tables": {"simulation_runs": []}}
            if "FROM experiments" in arguments["sql"]:
                return {"rows": [], "returned": 0}
            return {"rows": [{"value": 1}], "returned": 1}

        decision = asyncio.run(planner.propose(config, execute_tool))

        self.assertEqual(decision.proposal.rationale, "Bounded evidence.")
        self.assertEqual(
            len(decision.evidence),
            DScheduler.MAX_INVESTIGATION_ROUNDS + 1,
        )

    def test_duplicate_proposal_requires_one_reconsideration_and_reason(self) -> None:
        http = FakeHTTPClient()
        http.messages.append({
            "role": "assistant",
            "content": (
                '{"learning_rate":0.0008,"epsilon_start":0.9,'
                '"epsilon_decay":0.995,"rationale":"Repeat deliberately.",'
                '"duplicate_experiment_reason":"Verify deterministic reproduction '
                'after the deployment environment changed."}'
            ),
        })
        planner = LlamaPlanner(client=http)
        config = FakeExperimentControl().request(MessageType.GET_EXPERIMENT_CONFIG)

        async def execute_tool(name, arguments):
            if name == "get_database_schema":
                return {"tables": {"simulation_runs": [], "experiments": []}}
            if "FROM experiments" in arguments["sql"]:
                return {
                    "rows": [{"experiment_id": "experiment-1"}],
                    "returned": 1,
                }
            return {"rows": [{"count": 27}], "returned": 1}

        decision = asyncio.run(planner.propose(config, execute_tool))

        self.assertIn("deployment environment", decision.proposal.duplicate_experiment_reason)
        self.assertEqual(len(http.requests), 4)
        challenge = http.requests[-1][1]["messages"][-1]["content"]
        self.assertIn("experiment-1", challenge)
        self.assertEqual(
            decision.evidence[-1]["tool"],
            "duplicate_experiment_check",
        )

    def test_idle_cycle_reviews_history_and_starts_one_experiment(self) -> None:
        experiment = FakeExperimentControl()
        planner = FakePlanner()
        plans = MemoryPlanningRepository()
        scheduler = Scheduler(experiment, planner, plans)

        experiment_id = asyncio.run(scheduler.run_once())

        self.assertEqual(experiment_id, "experiment-2")
        self.assertEqual(len(planner.inputs), 1)
        self.assertEqual(planner.inputs[0]["learning_rate"], 0.001)
        self.assertEqual(
            experiment.calls,
            [
                (MessageType.GET_EXPERIMENT_STATUS, None),
                (MessageType.GET_EXPERIMENT_COUNT, None),
                (MessageType.GET_EXPERIMENT_CONFIG, None),
                (
                    MessageType.EXECUTE_READ_QUERY,
                    {"sql": "SELECT * FROM simulation_runs"},
                ),
                (
                    MessageType.SET_EXPERIMENT_CONFIG,
                    {
                        "learning_rate": 0.0008,
                        "epsilon_start": 0.9,
                        "epsilon_decay": 0.995,
                    },
                ),
                (
                    MessageType.START_EXPERIMENT,
                    {
                        "learning_rate": 0.0008,
                        "epsilon_start": 0.9,
                        "epsilon_decay": 0.995,
                    },
                ),
            ],
        )
        self.assertEqual(plans.started, [("plan-1", "experiment-2")])
        self.assertIn("rationale", plans.proposals[0][0])

    def test_fresh_install_starts_default_baseline_without_planner(self) -> None:
        experiment = FakeExperimentControl(experiment_count=0)
        planner = FakePlanner()
        plans = MemoryPlanningRepository()

        experiment_id = asyncio.run(
            Scheduler(experiment, planner, plans).run_once()
        )

        self.assertEqual(experiment_id, "experiment-2")
        self.assertEqual(planner.inputs, [])
        self.assertEqual(plans.proposals, [])
        self.assertEqual(
            experiment.calls,
            [
                (MessageType.GET_EXPERIMENT_STATUS, None),
                (MessageType.GET_EXPERIMENT_COUNT, None),
                (MessageType.GET_EXPERIMENT_CONFIG, None),
                (
                    MessageType.START_EXPERIMENT,
                    {
                        "learning_rate": 0.001,
                        "epsilon_start": 0.9,
                        "epsilon_decay": 0.995,
                    },
                ),
            ],
        )

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
        with self.assertRaisesRegex(PlanningError, "epsilon_decay"):
            ExperimentProposal.from_dict(
                {
                    "learning_rate": 0.001,
                    "epsilon_start": 0.9,
                    "epsilon_decay": 1.0,
                    "rationale": "Too short.",
                },
                config,
            )

    def test_default_schedule_checks_every_three_seconds(self) -> None:
        self.assertEqual(DScheduler.INITIAL_DELAY_SECONDS, 3)
        self.assertEqual(DScheduler.INTERVAL_SECONDS, 3)


if __name__ == "__main__":
    unittest.main()
