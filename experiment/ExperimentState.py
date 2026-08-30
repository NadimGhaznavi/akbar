"""In-memory live experiment state."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from experiment.ExperimentProtocol import ExperimentStatus


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ExperimentState:
    experiment_id: str
    status: ExperimentStatus
    config: dict[str, Any]
    epoch: int = 0
    score: int = 0
    highscore: int = 0
    progress: float = 0.0
    simulation_number: int = 0
    simulation_count: int = 0
    simulation_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


class ExperimentStateStore:
    def __init__(self) -> None:
        self._latest: ExperimentState | None = None

    def create(self, experiment_id: str, config: dict[str, Any]) -> ExperimentState:
        self._latest = ExperimentState(
            experiment_id=experiment_id,
            status=ExperimentStatus.QUEUED,
            config=config,
        )
        return self._latest

    def get(self, experiment_id: str | None = None) -> ExperimentState | None:
        if self._latest is None:
            return None
        if experiment_id is None or self._latest.experiment_id == experiment_id:
            return self._latest
        return None
