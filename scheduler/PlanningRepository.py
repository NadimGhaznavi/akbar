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
    def pending_evaluation(self) -> dict[str, Any] | None: ...
    def save_evaluation(
        self, plan_id: str, experiment_id: str, verdict: str, conclusion: str,
        evidence: list[dict[str, Any]],
    ) -> None: ...
    def ensure_initial_baseline_plan(self) -> None: ...


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
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_evaluations (
                    evaluation_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    plan_id CHAR(36) NOT NULL,
                    experiment_id CHAR(36) NOT NULL,
                    verdict VARCHAR(32) NOT NULL,
                    conclusion TEXT NOT NULL,
                    evidence_json LONGTEXT NOT NULL,
                    evaluation_version INT NOT NULL DEFAULT 1,
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    UNIQUE KEY uq_evaluation_plan_version (plan_id, evaluation_version),
                    INDEX idx_evaluation_experiment (experiment_id)
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

    def pending_evaluation(self) -> dict[str, Any] | None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.plan_id, p.experiment_id, p.proposal_json,
                       e.status AS experiment_status, e.error_text
                FROM experiment_plans p
                JOIN experiments e ON e.experiment_id = p.experiment_id
                LEFT JOIN experiment_evaluations v
                    ON v.plan_id = p.plan_id AND v.evaluation_version = 1
                WHERE p.status = 'started'
                    AND e.status IN ('completed', 'failed', 'cancelled', 'interrupted')
                    AND v.evaluation_id IS NULL
                ORDER BY e.completed_at ASC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "plan_id": row["plan_id"],
            "experiment_id": row["experiment_id"],
            "proposal": json.loads(row["proposal_json"]),
            "experiment_status": row["experiment_status"],
            "error": row["error_text"],
        }

    def save_evaluation(
        self, plan_id: str, experiment_id: str, verdict: str, conclusion: str,
        evidence: list[dict[str, Any]],
    ) -> None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO experiment_evaluations
                    (plan_id, experiment_id, verdict, conclusion, evidence_json)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (plan_id, experiment_id, verdict, conclusion,
                 json.dumps(evidence, separators=(",", ":"))),
            )

    def ensure_initial_baseline_plan(self) -> None:
        """Attach a scientific record to a legacy first experiment if needed."""
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT e.experiment_id, e.config_json
                FROM experiments e
                LEFT JOIN experiment_plans p ON p.experiment_id = e.experiment_id
                WHERE p.plan_id IS NULL
                ORDER BY e.created_at ASC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row is None:
                return
            config = json.loads(row["config_json"])
            proposal = {
                "learning_rate": config["learning_rate"],
                "epsilon_start": config["epsilon_start"],
                "epsilon_decay": config["epsilon_decay"],
                "rationale": (
                    "Run the service's default configuration to establish the "
                    "initial complete reference population for later experiments."
                ),
                "success_criterion": (
                    "All 27 configured simulations complete with seed 1970 and "
                    "produce a usable baseline population."
                ),
            }
            cursor.execute(
                """
                INSERT INTO experiment_plans
                    (plan_id, status, proposal_json, evidence_json, experiment_id,
                     completed_at)
                VALUES (%s, 'started', %s, '[]', %s, CURRENT_TIMESTAMP(6))
                """,
                (str(uuid4()), json.dumps(proposal, separators=(",", ":")),
                 row["experiment_id"]),
            )
