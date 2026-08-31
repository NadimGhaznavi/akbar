"""Replay-based temporal-difference trainer for the linear Q-model."""

from __future__ import annotations

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


@dataclass(frozen=True, slots=True)
class TransitionBatch:
    states: np.ndarray
    actions: np.ndarray
    rewards: np.ndarray
    next_states: np.ndarray
    dones: np.ndarray

    @classmethod
    def from_transitions(
        cls,
        transitions: tuple[Transition, ...],
    ) -> TransitionBatch:
        return cls(
            states=np.asarray(
                [item.state for item in transitions],
                dtype=np.float64,
            ),
            actions=np.fromiter(
                (item.action for item in transitions),
                dtype=np.int64,
                count=len(transitions),
            ),
            rewards=np.fromiter(
                (item.reward for item in transitions),
                dtype=np.float64,
                count=len(transitions),
            ),
            next_states=np.asarray(
                [item.next_state for item in transitions],
                dtype=np.float64,
            ),
            dones=np.fromiter(
                (item.done for item in transitions),
                dtype=np.float64,
                count=len(transitions),
            ),
        )

    def __len__(self) -> int:
        return len(self.actions)


class QTrainer:
    def __init__(self, model: LinearQModel, gamma: float, learning_rate: float) -> None:
        self.model = model
        self.gamma = gamma
        self.learning_rate = learning_rate

    def train(self, batch: TransitionBatch) -> float:
        next_values = np.max(self.model.predict(batch.next_states), axis=1)
        targets = batch.rewards + self.gamma * next_values * (1.0 - batch.dones)
        return self.model.train(
            batch.states,
            batch.actions,
            targets,
            self.learning_rate,
        )
