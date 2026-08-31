"""Bounded replay memory retained entirely in RAM."""

from __future__ import annotations

import random
from collections import deque
from collections.abc import Iterable, Iterator
from typing import Generic, TypeVar

T = TypeVar("T")


class ReplayMemory(Generic[T]):
    """Retain terminal-aligned, trainer-ready transition batches."""

    def __init__(
        self,
        capacity: int,
        batch_size: int,
        rng: random.Random,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if capacity < batch_size:
            raise ValueError("capacity must hold at least one batch")
        self.batch_size = batch_size
        self._batches: deque[tuple[T, ...]] = deque(
            maxlen=capacity // batch_size
        )
        self._rng = rng

    def append_episode(self, items: Iterable[T]) -> int:
        """Store complete batches ending at the episode's terminal move.

        Any incomplete chunk at the beginning of the episode is discarded so
        the final transition is always part of the final stored batch.
        """
        episode = tuple(items)
        retained = len(episode) - (len(episode) % self.batch_size)
        if retained == 0:
            return 0
        start = len(episode) - retained
        for offset in range(start, len(episode), self.batch_size):
            self._batches.append(episode[offset : offset + self.batch_size])
        return retained

    def sample_batch(self) -> tuple[T, ...]:
        if not self._batches:
            raise IndexError("cannot sample an empty replay memory")
        return self._rng.choice(self._batches)

    def batches(self) -> Iterator[tuple[T, ...]]:
        return iter(self._batches)

    def __len__(self) -> int:
        return len(self._batches) * self.batch_size
