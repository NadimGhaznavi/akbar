"""Validated configuration for an experiment run."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from constants.DExperiment import DExperiment


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    epochs: int = DExperiment.DEFAULT_EPOCHS
    epoch_delay: float = DExperiment.DEFAULT_EPOCH_DELAY
    seed: int = DExperiment.DEFAULT_SEED

    def __post_init__(self) -> None:
        if isinstance(self.epochs, bool) or not isinstance(self.epochs, int):
            raise TypeError("epochs must be an integer")
        if not 1 <= self.epochs <= DExperiment.MAX_EPOCHS:
            raise ValueError(
                f"epochs must be between 1 and {DExperiment.MAX_EPOCHS}"
            )
        if isinstance(self.epoch_delay, bool) or not isinstance(
            self.epoch_delay, (int, float)
        ):
            raise TypeError("epoch_delay must be a number")
        if not 0 <= float(self.epoch_delay) <= DExperiment.MAX_EPOCH_DELAY:
            raise ValueError(
                "epoch_delay must be between 0 and "
                f"{DExperiment.MAX_EPOCH_DELAY} seconds"
            )
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "ExperimentConfig":
        values = payload or {}
        unknown = set(values) - {"epochs", "epoch_delay", "seed"}
        if unknown:
            raise ValueError(f"unknown configuration fields: {', '.join(sorted(unknown))}")
        return cls(**values)

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)
