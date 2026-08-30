"""Bounded replay memory retained entirely in RAM."""

from __future__ import annotations

import random
from collections import deque
from typing import Generic, TypeVar

T = TypeVar("T")


class ReplayMemory(Generic[T]):
    def __init__(self, capacity: int, rng: random.Random) -> None:
        self._items: deque[T] = deque(maxlen=capacity)
        self._rng = rng

    def append(self, item: T) -> None:
        self._items.append(item)

    def sample(self, count: int) -> list[T]:
        count = min(count, len(self._items))
        return self._rng.sample(list(self._items), count)

    def __len__(self) -> int:
        return len(self._items)
