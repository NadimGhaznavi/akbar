from __future__ import annotations

import asyncio
import random
import unittest

from experiment.ExperimentConfig import ExperimentConfig
from snake_lab.game.SnakeGame import SnakeGame
from snake_lab.SnakeExperiment import SnakeExperiment


class SnakeGameTest(unittest.TestCase):
    def test_seed_reproduces_initial_state_and_food(self) -> None:
        first = SnakeGame(8, 10, random.Random(1970))
        second = SnakeGame(8, 10, random.Random(1970))
        self.assertEqual(first.state(), second.state())
        self.assertEqual(first.food, second.food)

    def test_wall_collision_ends_episode(self) -> None:
        game = SnakeGame(6, 100, random.Random(1))
        result = None
        for _ in range(4):
            result = game.step(0)
            if result.done:
                break
        self.assertIsNotNone(result)
        self.assertTrue(result.done)
        self.assertEqual(result.reason, "collision")


class SnakeExperimentTest(unittest.IsolatedAsyncioTestCase):
    async def test_fixed_seed_produces_repeatable_metrics(self) -> None:
        config = ExperimentConfig(
            epochs=4,
            seed=11,
            board_size=8,
            max_moves_multiplier=10,
            replay_capacity=100,
            batch_size=8,
        )

        async def run_once():
            telemetry = []

            async def collect(payload):
                telemetry.append(payload)

            result = await SnakeExperiment(config).run(asyncio.Event(), collect)
            return result, telemetry

        first_result, first_telemetry = await run_once()
        second_result, second_telemetry = await run_once()
        first_result.pop("elapsed_seconds")
        second_result.pop("elapsed_seconds")
        for payload in first_telemetry + second_telemetry:
            payload.pop("elapsed_seconds")
        self.assertEqual(first_result, second_result)
        self.assertEqual(first_telemetry, second_telemetry)


if __name__ == "__main__":
    unittest.main()
