"""Deterministic expansion of one proposal into simulation configurations."""

from __future__ import annotations

from dataclasses import replace
from itertools import product

from constants.DExperiment import DExperiment
from experiment.ExperimentConfig import ExperimentConfig


def _bounded_variants(
    value: float,
    minimum: float,
    maximum: float,
) -> tuple[float, float, float]:
    """Keep three distinct values when a submitted baseline is on a bound."""
    step = value * DExperiment.VARIATION_FRACTION
    low, middle, high = value - step, value, value + step
    if high > maximum:
        high = value
        middle = value - step
        low = value - (2 * step)
    if low < minimum:
        low = value
        middle = value + step
        high = value + (2 * step)
    if not minimum <= low < middle < high <= maximum:
        raise ValueError("submitted value is too close to its limits to vary")
    return low, middle, high


def build_simulation_configs(baseline: ExperimentConfig) -> list[ExperimentConfig]:
    """Return the 3 x 3 x 3 hyperparameter grid for the fixed seed.

    Epsilon decay is varied in terms of the amount decayed (``1 - decay``),
    which keeps useful values near one valid and symmetrically perturbed.
    """
    learning_rates = _bounded_variants(
        baseline.learning_rate,
        DExperiment.MIN_LEARNING_RATE,
        DExperiment.MAX_LEARNING_RATE,
    )
    epsilon_starts = _bounded_variants(
        baseline.epsilon_start,
        baseline.epsilon_min,
        1.0,
    )
    decay_amounts = _bounded_variants(1 - baseline.epsilon_decay, 0.0, 1.0)
    epsilon_decays = tuple(1 - amount for amount in reversed(decay_amounts))

    configs = []
    for learning_rate, epsilon_start, epsilon_decay in product(
        learning_rates,
        epsilon_starts,
        epsilon_decays,
    ):
        for seed in DExperiment.SEEDS:
            configs.append(
                replace(
                    baseline,
                    epochs=DExperiment.FIXED_EPOCHS,
                    seed=seed,
                    learning_rate=learning_rate,
                    epsilon_start=epsilon_start,
                    epsilon_decay=epsilon_decay,
                )
            )
    return configs
