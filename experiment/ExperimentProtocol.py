"""Versioned messages for the Akbar experiment control plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import json
from typing import Any
from uuid import uuid4

from constants.DExperiment import DExperiment


class MessageType(StrEnum):
    PING = "ping"
    PONG = "pong"
    START_EXPERIMENT = "start_experiment"
    EXPERIMENT_ACCEPTED = "experiment_accepted"
    GET_EXPERIMENT_STATUS = "get_experiment_status"
    EXPERIMENT_STATUS = "experiment_status"
    GET_EXPERIMENT_RESULT = "get_experiment_result"
    EXPERIMENT_RESULT = "experiment_result"
    GET_EXPERIMENT_COUNT = "get_experiment_count"
    EXPERIMENT_COUNT = "experiment_count"
    GET_CURRENT_HIGHSCORE = "get_current_highscore"
    CURRENT_HIGHSCORE = "current_highscore"
    STOP_EXPERIMENT = "stop_experiment"
    STOP_REQUESTED = "stop_requested"
    TELEMETRY = "telemetry"
    ERROR = "error"


class ExperimentStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class ProtocolError(ValueError):
    """A control-plane message is malformed or unsupported."""


@dataclass(frozen=True, slots=True)
class ExperimentMessage:
    message_type: MessageType
    payload: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid4()))
    experiment_id: str | None = None
    protocol_version: int = DExperiment.PROTOCOL_VERSION

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["message_type"] = self.message_type.value
        return data

    def to_json(self) -> bytes:
        return json.dumps(self.to_dict(), separators=(",", ":")).encode("utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentMessage":
        if not isinstance(data, dict):
            raise ProtocolError("message must be a JSON object")
        version = data.get("protocol_version")
        if version != DExperiment.PROTOCOL_VERSION:
            raise ProtocolError(f"unsupported protocol version: {version}")
        try:
            message_type = MessageType(data["message_type"])
        except KeyError as error:
            raise ProtocolError("message_type is required") from error
        except ValueError as error:
            raise ProtocolError(f"unknown message_type: {data.get('message_type')}") from error
        request_id = data.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise ProtocolError("request_id must be a non-empty string")
        payload = data.get("payload", {})
        if not isinstance(payload, dict):
            raise ProtocolError("payload must be an object")
        experiment_id = data.get("experiment_id")
        if experiment_id is not None and not isinstance(experiment_id, str):
            raise ProtocolError("experiment_id must be a string or null")
        return cls(
            message_type=message_type,
            payload=payload,
            request_id=request_id,
            experiment_id=experiment_id,
            protocol_version=version,
        )

    @classmethod
    def from_json(cls, data: bytes) -> "ExperimentMessage":
        try:
            decoded = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ProtocolError(f"invalid JSON message: {error}") from error
        return cls.from_dict(decoded)

    def reply(
        self,
        message_type: MessageType,
        payload: dict[str, Any] | None = None,
        experiment_id: str | None = None,
    ) -> "ExperimentMessage":
        return ExperimentMessage(
            message_type=message_type,
            payload=payload or {},
            request_id=self.request_id,
            experiment_id=experiment_id if experiment_id is not None else self.experiment_id,
        )
