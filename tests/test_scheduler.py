from __future__ import annotations

import asyncio
import unittest
from typing import Any

from scheduler.SchedulerServer import Scheduler


class MemoryAgentRepository:
    def __init__(self) -> None:
        self.active = False
        self.enqueued: list[tuple[str, str]] = []

    def initialize(self) -> None:
        pass

    def mark_interrupted(self) -> None:
        pass

    def enqueue(self, prompt: str, source: str) -> str | None:
        if self.active:
            return None
        self.active = True
        self.enqueued.append((prompt, source))
        return "turn-1"

    def claim_next(self) -> dict[str, Any] | None:
        return None

    def finish(
        self,
        turn_id: str,
        status: str,
        response: str | None = None,
        error: str | None = None,
    ) -> None:
        pass


class SchedulerTest(unittest.TestCase):
    def test_enqueue_once_creates_durable_scheduler_turn(self) -> None:
        repository = MemoryAgentRepository()
        scheduler = Scheduler(repository)

        self.assertEqual(asyncio.run(scheduler.enqueue_once()), "turn-1")
        self.assertEqual(repository.enqueued, [(scheduler.prompt, "scheduler")])

    def test_enqueue_once_skips_when_turn_is_active(self) -> None:
        repository = MemoryAgentRepository()
        repository.active = True

        self.assertIsNone(asyncio.run(Scheduler(repository).enqueue_once()))
        self.assertEqual(repository.enqueued, [])

    def test_scheduler_rejects_unsafe_timing_values(self) -> None:
        repository = MemoryAgentRepository()
        with self.assertRaisesRegex(ValueError, "interval must be positive"):
            Scheduler(repository, interval_seconds=0)

    def test_default_prompt_encodes_the_safe_decision_cycle(self) -> None:
        prompt = Scheduler(MemoryAgentRepository()).prompt
        self.assertIn("queued or running", prompt)
        self.assertIn("review recent completed results", prompt)
        self.assertIn("start exactly one experiment", prompt)
        self.assertIn("rationale", prompt)


if __name__ == "__main__":
    unittest.main()
