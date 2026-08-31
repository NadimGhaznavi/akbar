"""Replay-based temporal-difference trainer for the linear Q-model."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from snake_lab.models.LinearQModel import LinearQModel


@dataclass(frozen=True, slots=True)
class Transition:
    state: tuple[float, ...]
    action: int
    reward: float
    next_state: tuple[float, ...]
    done: bool


class QTrainer:
    def __init__(self, model: LinearQModel, gamma: float, learning_rate: float) -> None:
        self.model = model
        self.gamma = gamma
        self.learning_rate = learning_rate

    def train(self, transitions: Sequence[Transition]) -> float:
        states = np.asarray([item.state for item in transitions], dtype=np.float64)
        next_states = np.asarray(
            [item.next_state for item in transitions],
            dtype=np.float64,
        )
        actions = np.asarray([item.action for item in transitions], dtype=np.int64)
        rewards = np.asarray([item.reward for item in transitions], dtype=np.float64)
        dones = np.asarray([item.done for item in transitions], dtype=np.float64)
        next_values = np.max(self.model.predict(next_states), axis=1)
        targets = rewards + self.gamma * next_values * (1.0 - dones)
        return self.model.train(states, actions, targets, self.learning_rate)
