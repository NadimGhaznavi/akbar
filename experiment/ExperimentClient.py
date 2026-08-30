"""Synchronous client for the experiment control plane."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import zmq

from constants.DExperiment import DExperiment
from experiment.ExperimentProtocol import ExperimentMessage, MessageType


class ExperimentClientError(RuntimeError):
    pass


class ExperimentClient:
    def __init__(
        self,
        endpoint: str = DExperiment.CONTROL_ENDPOINT,
        timeout_ms: int = DExperiment.CLIENT_TIMEOUT_MS,
    ) -> None:
        self.endpoint = endpoint
        self.timeout_ms = timeout_ms

    def request(
        self,
        message_type: MessageType,
        payload: dict[str, Any] | None = None,
        experiment_id: str | None = None,
    ) -> dict[str, Any]:
        request = ExperimentMessage(
            message_type=message_type,
            payload=payload or {},
            experiment_id=experiment_id,
        )
        context = zmq.Context.instance()
        socket = context.socket(zmq.DEALER)
        socket.setsockopt(zmq.IDENTITY, f"akbar-tool-{uuid4()}".encode())
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(self.endpoint)
        try:
            socket.send(request.to_json())
            if not socket.poll(self.timeout_ms, zmq.POLLIN):
                raise ExperimentClientError("experiment service request timed out")
            reply = ExperimentMessage.from_json(socket.recv())
        finally:
            socket.close()

        if reply.request_id != request.request_id:
            raise ExperimentClientError("experiment service returned a mismatched request")
        if reply.message_type is MessageType.ERROR:
            raise ExperimentClientError(reply.payload.get("error", "experiment service error"))
        response = dict(reply.payload)
        if reply.experiment_id is not None:
            response.setdefault("experiment_id", reply.experiment_id)
        return response
