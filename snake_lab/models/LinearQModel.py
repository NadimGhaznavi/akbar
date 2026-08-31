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

    def predict_one(self, state: tuple[float, ...]) -> FloatArray:
        return np.asarray(state, dtype=np.float64) @ self.weights + self.bias

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
        action_gradients = np.zeros(
            (len(states), self.bias.size),
            dtype=np.float64,
        )
        action_gradients[np.arange(len(states)), actions] = gradient
        weight_gradient = states.T @ action_gradients
        bias_gradient = np.sum(action_gradients, axis=0)
        self.weights -= learning_rate * np.clip(weight_gradient, -1.0, 1.0)
        self.bias -= learning_rate * np.clip(bias_gradient, -1.0, 1.0)
        return loss
