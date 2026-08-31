"""One fully in-memory AI Snake training experiment."""

from __future__ import annotations

import asyncio
import random
import statistics
import time
from collections.abc import Awaitable, Callable
from typing import Any

import numpy as np

from experiment.ExperimentConfig import ExperimentConfig
from experiment.ExperimentRunner import ExperimentCancelled
from snake_lab.game.SnakeGame import SnakeGame
from snake_lab.models.LinearQModel import LinearQModel
from snake_lab.training.QTrainer import QTrainer, Transition
from snake_lab.training.ReplayMemory import ReplayMemory

TelemetryCallback = Callable[[dict[str, Any]], Awaitable[None]]


class SnakeExperiment:
    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    async def run(
        self,
        stop_event: asyncio.Event,
        publish_telemetry: TelemetryCallback,
    ) -> dict[str, Any]:
        policy_rng = random.Random(self.config.seed)
        game_rng = random.Random(self.config.seed + 1)
        replay_rng = random.Random(self.config.seed + 2)
        game = SnakeGame(
            self.config.board_size,
            self.config.max_moves_multiplier,
            game_rng,
        )
        model = LinearQModel(game.STATE_SIZE, game.ACTION_COUNT, self.config.seed)
        trainer = QTrainer(model, self.config.gamma, self.config.learning_rate)
        memory: ReplayMemory[Transition] = ReplayMemory(
            self.config.replay_capacity,
            self.config.batch_size,
            replay_rng,
        )

        scores: list[int] = []
        losses: list[float] = []
        highscore = 0
        total_moves = 0
        started = time.monotonic()

        for epoch in range(1, self.config.epochs + 1):
            state = game.reset()
            done = False
            episode: list[Transition] = []
            epsilon = max(
                self.config.epsilon_min,
                self.config.epsilon_start
                * (self.config.epsilon_decay ** (epoch - 1)),
            )
            while not done:
                if stop_event.is_set():
                    raise ExperimentCancelled()
                if policy_rng.random() < epsilon:
                    action = policy_rng.randrange(game.ACTION_COUNT)
                else:
                    values = model.predict(np.asarray([state], dtype=np.float64))[0]
                    action = int(np.argmax(values))

                step = game.step(action)
                transition = Transition(
                    state,
                    action,
                    step.reward,
                    step.state,
                    step.done,
                )
                episode.append(transition)
                state = step.state
                done = step.done
                total_moves += 1
                if total_moves % 256 == 0:
                    await asyncio.sleep(0)

            memory.append_episode(episode)
            episode_losses = (
                [trainer.train(memory.sample_batch())] if len(memory) else []
            )
            scores.append(game.score)
            losses.extend(episode_losses)
            highscore = max(highscore, game.score)
            await publish_telemetry(
                {
                    "epoch": epoch,
                    "score": game.score,
                    "highscore": highscore,
                    "average_score": round(statistics.fmean(scores), 6),
                    "average_loss": (
                        round(statistics.fmean(episode_losses), 6)
                        if episode_losses
                        else 0.0
                    ),
                    "epsilon": round(epsilon, 6),
                    "moves": game.moves,
                    "progress": epoch / self.config.epochs,
                    "elapsed_seconds": round(time.monotonic() - started, 6),
                }
            )
            # Give the control plane a scheduling point between epochs so a
            # stop request is observed without adding I/O to the hot loop.
            await asyncio.sleep(0)

        return {
            "epochs": self.config.epochs,
            "highscore": highscore,
            "average_score": round(statistics.fmean(scores), 6),
            "average_loss": round(statistics.fmean(losses), 6) if losses else 0.0,
            "total_moves": total_moves,
            "replay_size": len(memory),
            "elapsed_seconds": round(time.monotonic() - started, 6),
        }
