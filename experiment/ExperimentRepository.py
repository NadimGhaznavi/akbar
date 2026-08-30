"""MariaDB persistence at experiment lifecycle boundaries."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol

from constants.DExperiment import DExperiment
from database.Database import connect


class ExperimentRepository(Protocol):
    def initialize(self) -> None: ...
    def mark_interrupted(self) -> None: ...
    def load_config(self) -> dict[str, Any] | None: ...
    def save_config(self, config: dict[str, Any]) -> None: ...
    def create(self, experiment_id: str, config: dict[str, Any]) -> None: ...
    def mark_running(self, experiment_id: str) -> None: ...
    def finish(
        self,
        experiment_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None: ...
    def get(self, experiment_id: str) -> dict[str, Any] | None: ...
    def count(self) -> int: ...
    def resolve_suffix(self, suffix: str) -> list[str]: ...
    def create_simulation(
        self, simulation_id: str, experiment_id: str, config: dict[str, Any]
    ) -> None: ...
    def finish_simulation(
        self, simulation_id: str, status: str,
        result: dict[str, Any] | None = None, error: str | None = None,
    ) -> None: ...
    def schema(self) -> list[dict[str, Any]]: ...
    def execute_read_query(
        self, sql: str, parameters: dict[str, Any] | list[Any] | None, max_rows: int
    ) -> dict[str, Any]: ...


class MariaDBExperimentRepository:
    def _connect(self):
        return connect()

    def initialize(self) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS experiments (
                    experiment_id CHAR(36) PRIMARY KEY,
                    status VARCHAR(32) NOT NULL,
                    config_json LONGTEXT NOT NULL,
                    result_json LONGTEXT NULL,
                    error_text TEXT NULL,
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    started_at DATETIME(6) NULL,
                    completed_at DATETIME(6) NULL,
                    INDEX idx_experiments_status (status),
                    INDEX idx_experiments_created_at (created_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS simulation_runs (
                    simulation_id CHAR(36) PRIMARY KEY,
                    experiment_id CHAR(36) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    seed BIGINT NOT NULL,
                    epochs INT NOT NULL,
                    learning_rate DOUBLE NOT NULL,
                    epsilon_start DOUBLE NOT NULL,
                    epsilon_decay DOUBLE NOT NULL,
                    epochs_completed INT NULL,
                    highscore INT NULL,
                    average_score DOUBLE NULL,
                    average_loss DOUBLE NULL,
                    total_moves BIGINT NULL,
                    replay_size INT NULL,
                    elapsed_seconds DOUBLE NULL,
                    config_json LONGTEXT NOT NULL,
                    result_json LONGTEXT NULL,
                    error_text TEXT NULL,
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    started_at DATETIME(6) NULL,
                    completed_at DATETIME(6) NULL,
                    INDEX idx_simulation_experiment (experiment_id),
                    INDEX idx_simulation_status (status),
                    CONSTRAINT fk_simulation_experiment FOREIGN KEY (experiment_id)
                        REFERENCES experiments (experiment_id)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS experiment_configuration (
                    config_name VARCHAR(32) PRIMARY KEY,
                    config_json LONGTEXT NOT NULL,
                    updated_at DATETIME(6) NOT NULL
                        DEFAULT CURRENT_TIMESTAMP(6)
                        ON UPDATE CURRENT_TIMESTAMP(6)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )

    def mark_interrupted(self) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE experiments
                SET status = 'interrupted', completed_at = CURRENT_TIMESTAMP(6),
                    error_text = 'Experiment service restarted during execution'
                WHERE status IN ('queued', 'running')
                """
            )
            cursor.execute(
                """
                UPDATE simulation_runs
                SET status = 'interrupted', completed_at = CURRENT_TIMESTAMP(6),
                    error_text = 'Experiment service restarted during execution'
                WHERE status IN ('queued', 'running')
                """
            )

    def load_config(self) -> dict[str, Any] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT config_json
                FROM experiment_configuration
                WHERE config_name = 'active'
                """
            )
            row = cursor.fetchone()
        return json.loads(row["config_json"]) if row is not None else None

    def save_config(self, config: dict[str, Any]) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO experiment_configuration (config_name, config_json)
                VALUES ('active', %s)
                ON DUPLICATE KEY UPDATE config_json = VALUES(config_json)
                """,
                (json.dumps(config, separators=(",", ":")),),
            )

    def create(self, experiment_id: str, config: dict[str, Any]) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO experiments (experiment_id, status, config_json)
                VALUES (%s, 'queued', %s)
                """,
                (experiment_id, json.dumps(config, separators=(",", ":"))),
            )

    def mark_running(self, experiment_id: str) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE experiments
                SET status = 'running', started_at = CURRENT_TIMESTAMP(6)
                WHERE experiment_id = %s
                """,
                (experiment_id,),
            )

    def finish(
        self,
        experiment_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        result_json = (
            json.dumps(result, separators=(",", ":")) if result is not None else None
        )
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE experiments
                SET status = %s, result_json = %s, error_text = %s,
                    completed_at = CURRENT_TIMESTAMP(6)
                WHERE experiment_id = %s
                """,
                (status, result_json, error, experiment_id),
            )

    def get(self, experiment_id: str) -> dict[str, Any] | None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT experiment_id, status, config_json, result_json, error_text,
                       created_at, started_at, completed_at
                FROM experiments WHERE experiment_id = %s
                """,
                (experiment_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return {
            "experiment_id": row["experiment_id"],
            "status": row["status"],
            "config": json.loads(row["config_json"]),
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error": row["error_text"],
            "created_at": row["created_at"].isoformat(),
            "started_at": row["started_at"].isoformat() if row["started_at"] else None,
            "completed_at": (
                row["completed_at"].isoformat() if row["completed_at"] else None
            ),
        }

    def count(self) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS experiment_count FROM experiments")
            row = cursor.fetchone()
        return int(row["experiment_count"])

    def resolve_suffix(self, suffix: str) -> list[str]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT experiment_id
                FROM experiments
                WHERE experiment_id LIKE %s
                ORDER BY created_at DESC
                LIMIT 2
                """,
                (f"%{suffix}",),
            )
            rows = cursor.fetchall()
        return [str(row["experiment_id"]) for row in rows]

    def create_simulation(
        self,
        simulation_id: str,
        experiment_id: str,
        config: dict[str, Any],
    ) -> None:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO simulation_runs (
                    simulation_id, experiment_id, status, seed, epochs,
                    learning_rate, epsilon_start, epsilon_decay, config_json,
                    started_at
                ) VALUES (%s, %s, 'running', %s, %s, %s, %s, %s, %s,
                          CURRENT_TIMESTAMP(6))
                """,
                (
                    simulation_id,
                    experiment_id,
                    config["seed"],
                    config["epochs"],
                    config["learning_rate"],
                    config["epsilon_start"],
                    config["epsilon_decay"],
                    json.dumps(config, separators=(",", ":")),
                ),
            )

    def finish_simulation(
        self,
        simulation_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        result_json = json.dumps(result, separators=(",", ":")) if result else None
        metrics = result.get("metrics", {}) if result else {}
        timing = result.get("timing", {}) if result else {}
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE simulation_runs
                SET status = %s, result_json = %s, error_text = %s,
                    epochs_completed = %s, highscore = %s,
                    average_score = %s, average_loss = %s,
                    total_moves = %s, replay_size = %s, elapsed_seconds = %s,
                    completed_at = CURRENT_TIMESTAMP(6)
                WHERE simulation_id = %s
                """,
                (
                    status,
                    result_json,
                    error,
                    metrics.get("epochs_completed"),
                    metrics.get("highscore"),
                    metrics.get("average_score"),
                    metrics.get("average_loss"),
                    metrics.get("total_moves"),
                    metrics.get("replay_size"),
                    timing.get("elapsed_seconds"),
                    simulation_id,
                ),
            )

    def schema(self) -> list[dict[str, Any]]:
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT TABLE_NAME AS table_name, COLUMN_NAME AS column_name,
                       DATA_TYPE AS data_type, IS_NULLABLE AS is_nullable,
                       COLUMN_KEY AS column_key
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """
            )
            return list(cursor.fetchall())

    def execute_read_query(
        self,
        sql: str,
        parameters: dict[str, Any] | list[Any] | None,
        max_rows: int,
    ) -> dict[str, Any]:
        statement = validate_read_query(sql)
        with self._connect() as connection, connection.cursor() as cursor:
            try:
                cursor.execute(
                    "SET SESSION max_statement_time = %s",
                    (DExperiment.QUERY_TIMEOUT_SECONDS,),
                )
                cursor.execute("START TRANSACTION READ ONLY")
                cursor.execute(statement, parameters or ())
                columns = [item[0] for item in cursor.description or ()]
                rows = [
                    {key: _json_value(value) for key, value in row.items()}
                    for row in cursor.fetchmany(max_rows + 1)
                ]
            finally:
                connection.rollback()
        truncated = len(rows) > max_rows
        return {
            "columns": columns,
            "rows": rows[:max_rows],
            "returned": min(len(rows), max_rows),
            "truncated": truncated,
        }


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def validate_read_query(sql: str) -> str:
    statement = sql.strip()
    without_comments = re.sub(r"/\*.*?\*/|--[^\r\n]*|#[^\r\n]*", " ", statement, flags=re.S)
    normalized = " ".join(without_comments.split()).lower()
    if not normalized.lstrip("(").startswith(("select", "with")):
        raise ValueError("only SELECT statements and read-only CTEs are allowed")
    if ";" in statement.rstrip("; \t\r\n"):
        raise ValueError("exactly one SQL statement is allowed")
    if re.search(r"\binto\s+(?:out|dump)file\b|\bload_file\s*\(", normalized):
        raise ValueError("server filesystem access is not allowed")
    return statement
