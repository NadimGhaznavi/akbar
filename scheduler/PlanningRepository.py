"""Persist scheduler planning decisions in MariaDB."""

from __future__ import annotations

import json
from typing import Any, Protocol
from uuid import uuid4

from database.Database import connect


class PlanningRepository(Protocol):
    def initialize(self) -> None: ...
    def create(
        self,
        proposal: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> str: ...
    def mark_started(self, plan_id: str, experiment_id: str) -> None: ...
    def mark_failed(self, plan_id: str, error: str) -> None: ...


class MariaDBPlanningRepository:
    def initialize(self) -> None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS agent_turns")
            cursor.execute("DROP TABLE IF EXISTS agent_turn_gate")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_plans (
                    plan_id CHAR(36) PRIMARY KEY,
                    status VARCHAR(32) NOT NULL,
                    proposal_json LONGTEXT NOT NULL,
                    evidence_json LONGTEXT NOT NULL,
                    experiment_id CHAR(36) NULL,
                    error_text TEXT NULL,
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    completed_at DATETIME(6) NULL,
                    INDEX idx_experiment_plans_created (created_at),
                    INDEX idx_experiment_plans_experiment (experiment_id)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )

    def create(
        self,
        proposal: dict[str, Any],
        evidence: list[dict[str, Any]],
    ) -> str:
        plan_id = str(uuid4())
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO experiment_plans
                    (plan_id, status, proposal_json, evidence_json)
                VALUES (%s, 'proposed', %s, %s)
                """,
                (
                    plan_id,
                    json.dumps(proposal, separators=(",", ":")),
                    json.dumps(evidence, separators=(",", ":")),
                ),
            )
        return plan_id

    def mark_started(self, plan_id: str, experiment_id: str) -> None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE experiment_plans
                SET status = 'started', experiment_id = %s,
                    completed_at = CURRENT_TIMESTAMP(6)
                WHERE plan_id = %s
                """,
                (experiment_id, plan_id),
            )

    def mark_failed(self, plan_id: str, error: str) -> None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE experiment_plans
                SET status = 'failed', error_text = %s,
                    completed_at = CURRENT_TIMESTAMP(6)
                WHERE plan_id = %s
                """,
                (error, plan_id),
            )
