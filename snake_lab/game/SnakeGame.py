"""Deterministic, headless Snake game mechanics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import random


@dataclass(frozen=True, slots=True)
class Position:
    x: int
    y: int


class Direction(IntEnum):
    RIGHT = 0
    DOWN = 1
    LEFT = 2
    UP = 3


_DIRECTION_VECTORS = {
    Direction.RIGHT: Position(1, 0),
    Direction.DOWN: Position(0, 1),
    Direction.LEFT: Position(-1, 0),
    Direction.UP: Position(0, -1),
}


@dataclass(frozen=True, slots=True)
class StepResult:
    state: tuple[float, ...]
    reward: float
    score: int
    done: bool
    reason: str | None


class SnakeGame:
    STATE_SIZE = 11
    ACTION_COUNT = 3

    def __init__(
        self,
        board_size: int,
        max_moves_multiplier: int,
        rng: random.Random,
    ) -> None:
        if board_size < 6:
            raise ValueError("board_size must be at least 6")
        self.board_size = board_size
        self.max_moves_multiplier = max_moves_multiplier
        self.rng = rng
        self.reset()

    def reset(self) -> tuple[float, ...]:
        center = self.board_size // 2
        self.direction = Direction.RIGHT
        self.head = Position(center, center)
        self.body = [Position(center - 1, center), Position(center - 2, center)]
        self.score = 0
        self.moves = 0
        self.food = self._place_food()
        return self.state()

    def state(self) -> tuple[float, ...]:
        straight = self.direction
        right = Direction((int(self.direction) + 1) % 4)
        left = Direction((int(self.direction) - 1) % 4)
        return (
            float(self._danger(straight)),
            float(self._danger(right)),
            float(self._danger(left)),
            float(self.direction is Direction.LEFT),
            float(self.direction is Direction.RIGHT),
            float(self.direction is Direction.UP),
            float(self.direction is Direction.DOWN),
            float(self.food.x < self.head.x),
            float(self.food.x > self.head.x),
            float(self.food.y < self.head.y),
            float(self.food.y > self.head.y),
        )

    def step(self, action: int) -> StepResult:
        if action not in range(self.ACTION_COUNT):
            raise ValueError("action must be 0 (straight), 1 (right), or 2 (left)")
        if action == 1:
            self.direction = Direction((int(self.direction) + 1) % 4)
        elif action == 2:
            self.direction = Direction((int(self.direction) - 1) % 4)

        vector = _DIRECTION_VECTORS[self.direction]
        new_head = Position(self.head.x + vector.x, self.head.y + vector.y)
        self.moves += 1
        if self._collision(new_head):
            return StepResult(self.state(), -10.0, self.score, True, "collision")
        if self.moves > self.max_moves_multiplier * (len(self.body) + 1):
            return StepResult(self.state(), -10.0, self.score, True, "max_moves")

        old_distance = self._distance(self.head, self.food)
        self.body.insert(0, self.head)
        self.head = new_head
        if self.head == self.food:
            self.score += 1
            reward = 10.0
            self.food = self._place_food()
        else:
            self.body.pop()
            new_distance = self._distance(self.head, self.food)
            reward = 1.0 if new_distance < old_distance else -1.0
        return StepResult(self.state(), reward, self.score, False, None)

    def _danger(self, direction: Direction) -> bool:
        vector = _DIRECTION_VECTORS[direction]
        return self._collision(Position(self.head.x + vector.x, self.head.y + vector.y))

    def _collision(self, position: Position) -> bool:
        return (
            position.x < 0
            or position.y < 0
            or position.x >= self.board_size
            or position.y >= self.board_size
            or position in self.body
        )

    def _place_food(self) -> Position:
        occupied = {self.head, *self.body}
        available = [
            Position(x, y)
            for x in range(self.board_size)
            for y in range(self.board_size)
            if Position(x, y) not in occupied
        ]
        if not available:
            raise RuntimeError("the snake occupies the complete board")
        return self.rng.choice(available)

    @staticmethod
    def _distance(first: Position, second: Position) -> int:
        return abs(first.x - second.x) + abs(first.y - second.y)
