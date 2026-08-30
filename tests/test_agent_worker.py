from __future__ import annotations

import asyncio
import unittest
from typing import Any

from agent.AgentServer import AgentWorker


class MemoryAgentRepository:
    def __init__(self, turn: dict[str, Any] | None) -> None:
        self.turn = turn
        self.finished: list[tuple[str, str, str | None, str | None]] = []

    def initialize(self) -> None:
        pass

    def mark_interrupted(self) -> None:
        pass

    def enqueue(self, prompt: str, source: str) -> str | None:
        return None

    def claim_next(self) -> dict[str, Any] | None:
        turn, self.turn = self.turn, None
        return turn

    def finish(
        self,
        turn_id: str,
        status: str,
        response: str | None = None,
        error: str | None = None,
    ) -> None:
        self.finished.append((turn_id, status, response, error))


class FakeAgent:
    async def run(self, prompt: str) -> str:
        return f"Handled: {prompt}"


class FailingAgent:
    async def run(self, prompt: str) -> str:
        raise OSError("model unavailable")


class AgentWorkerTest(unittest.TestCase):
    def test_worker_claims_and_completes_turn(self) -> None:
        repository = MemoryAgentRepository(
            {"turn_id": "turn-1", "source": "scheduler", "prompt": "Continue"}
        )

        processed = asyncio.run(AgentWorker(repository, FakeAgent()).process_one())

        self.assertTrue(processed)
        self.assertEqual(
            repository.finished,
            [("turn-1", "completed", "Handled: Continue", None)],
        )

    def test_worker_persists_agent_failure(self) -> None:
        repository = MemoryAgentRepository(
            {"turn_id": "turn-1", "source": "scheduler", "prompt": "Continue"}
        )

        asyncio.run(AgentWorker(repository, FailingAgent()).process_one())

        self.assertEqual(
            repository.finished,
            [("turn-1", "failed", None, "model unavailable")],
        )


if __name__ == "__main__":
    unittest.main()
