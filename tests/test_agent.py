from __future__ import annotations

import copy
import unittest
from typing import Any

from agent.AkbarAgent import AgentError, AkbarAgent


class FakeChat:
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self.responses = responses
        self.requests: list[dict[str, Any]] = []

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.requests.append(
            {"messages": copy.deepcopy(messages), "tools": copy.deepcopy(tools)}
        )
        return self.responses.pop(0)


class FakeTools:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_experiment_count",
                    "description": "Count experiments.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        return {"experiment_count": 3}


class ExperimentTools:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "start_experiment",
                    "description": "Start an experiment.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        self.calls.append((name, arguments))
        return {
            "isError": False,
            "structuredContent": {
                "result": {"status": "queued", "experiment_id": "experiment-1"}
            },
        }


def chat_response(message: dict[str, Any]) -> dict[str, Any]:
    return {"choices": [{"message": message}]}


class AgentTest(unittest.IsolatedAsyncioTestCase):
    async def test_agent_executes_tool_and_returns_final_response(self) -> None:
        chat = FakeChat(
            [
                chat_response(
                    {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "get_experiment_count",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    }
                ),
                chat_response({"content": "Three experiments are recorded."}),
            ]
        )
        tools = FakeTools()

        result = await AkbarAgent(chat, tools).run("Continue.")

        self.assertEqual(result, "Three experiments are recorded.")
        self.assertEqual(tools.calls, [("get_experiment_count", {})])
        second_messages = chat.requests[1]["messages"]
        self.assertEqual(second_messages[-1]["role"], "tool")
        self.assertEqual(second_messages[-1]["tool_call_id"], "call-1")
        self.assertEqual(
            second_messages[-1]["content"],
            '{"experiment_count":3}',
        )

    async def test_agent_rejects_unknown_tool(self) -> None:
        chat = FakeChat(
            [
                chat_response(
                    {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "delete_everything",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    }
                )
            ]
        )
        with self.assertRaisesRegex(AgentError, "unknown tool"):
            await AkbarAgent(chat, FakeTools()).run("Continue.")

    async def test_agent_enforces_total_tool_call_limit(self) -> None:
        chat = FakeChat(
            [
                chat_response(
                    {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "get_experiment_count",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    }
                )
            ]
        )
        with self.assertRaisesRegex(AgentError, "maximum total tool calls"):
            await AkbarAgent(chat, FakeTools(), max_tool_calls=0).run("Continue.")

    async def test_scheduled_turn_cannot_finish_before_starting_work(self) -> None:
        chat = FakeChat(
            [
                chat_response({"content": "Nothing is currently running."}),
                chat_response(
                    {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "start_experiment",
                                    "arguments": "{}",
                                },
                            }
                        ],
                    }
                ),
                chat_response(
                    {"content": "Started experiment experiment-1."}
                ),
            ]
        )
        tools = ExperimentTools()

        result = await AkbarAgent(chat, tools).run(
            "Continue.",
            require_experiment_resolution=True,
        )

        self.assertEqual(result, "Started experiment experiment-1.")
        self.assertEqual(tools.calls, [("start_experiment", {})])
        self.assertIn(
            "call start_experiment",
            chat.requests[1]["messages"][-1]["content"],
        )


if __name__ == "__main__":
    unittest.main()
