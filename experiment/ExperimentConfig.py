"""Validated configuration for an experiment run."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from constants.DExperiment import DExperiment


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    epochs: int = DExperiment.DEFAULT_EPOCHS
    seed: int = DExperiment.DEFAULT_SEED
    board_size: int = 20
    max_moves_multiplier: int = 100
    replay_capacity: int = 10_000
    batch_size: int = 64
    gamma: float = 0.9
    learning_rate: float = 0.001
    epsilon_start: float = 1.0
    epsilon_min: float = 0.01
    epsilon_decay: float = 0.995

    def __post_init__(self) -> None:
        if isinstance(self.epochs, bool) or not isinstance(self.epochs, int):
            raise TypeError("epochs must be an integer")
        if not 1 <= self.epochs <= DExperiment.MAX_EPOCHS:
            raise ValueError(
                f"epochs must be between 1 and {DExperiment.MAX_EPOCHS}"
            )
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")
        if not 6 <= self.board_size <= 100:
            raise ValueError("board_size must be between 6 and 100")
        if self.max_moves_multiplier < 1:
            raise ValueError("max_moves_multiplier must be positive")
        if self.replay_capacity < 1:
            raise ValueError("replay_capacity must be positive")
        if not 1 <= self.batch_size <= self.replay_capacity:
            raise ValueError("batch_size must fit within replay_capacity")
        if not 0 <= self.gamma <= 1:
            raise ValueError("gamma must be between 0 and 1")
        if self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive")
        if not 0 <= self.epsilon_min <= self.epsilon_start <= 1:
            raise ValueError("epsilon values must satisfy 0 <= min <= start <= 1")
        if not 0 < self.epsilon_decay <= 1:
            raise ValueError("epsilon_decay must be greater than 0 and at most 1")

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ExperimentConfig":
        values = payload or {}
        unknown = set(values) - set(cls.__dataclass_fields__)
        if unknown:
            raise ValueError(f"unknown configuration fields: {', '.join(sorted(unknown))}")
        return cls(**values)

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)
