"""A compact NumPy linear Q-function with no artifact persistence."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


class LinearQModel:
    def __init__(self, input_size: int, action_count: int, seed: int) -> None:
        rng = np.random.default_rng(seed)
        self.weights: FloatArray = rng.normal(
            0.0,
            0.01,
            size=(input_size, action_count),
        )
        self.bias: FloatArray = np.zeros(action_count, dtype=np.float64)

    def predict(self, states: FloatArray) -> FloatArray:
        return states @ self.weights + self.bias

    def train(
        self,
        states: FloatArray,
        actions: NDArray[np.int64],
        targets: FloatArray,
        learning_rate: float,
    ) -> float:
        predictions = self.predict(states)
        selected = predictions[np.arange(len(states)), actions]
        errors = np.clip(selected - targets, -10.0, 10.0)
        loss = float(np.mean(errors**2))

        gradient = (2.0 / len(states)) * errors
        weight_gradient = np.zeros_like(self.weights)
        bias_gradient = np.zeros_like(self.bias)
        for row, action, value in zip(states, actions, gradient, strict=True):
            weight_gradient[:, action] += row * value
            bias_gradient[action] += value
        self.weights -= learning_rate * np.clip(weight_gradient, -1.0, 1.0)
        self.bias -= learning_rate * np.clip(bias_gradient, -1.0, 1.0)
        return loss
