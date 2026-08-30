"""MariaDB persistence at experiment lifecycle boundaries."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol

import pymysql
from pymysql.cursors import DictCursor

from constants.DDatabase import DDatabase
from constants.DExperiment import DExperiment


class ExperimentRepository(Protocol):
    def initialize(self) -> None: ...
    def mark_interrupted(self) -> None: ...
    def allocate_seed(self) -> int: ...
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


class MariaDBExperimentRepository:
    def _connect(self):
        return pymysql.connect(
            host=os.getenv("AKBAR_DB_HOST", DDatabase.HOST),
            port=int(os.getenv("AKBAR_DB_PORT", str(DDatabase.PORT))),
            user=os.getenv("AKBAR_DB_USER", DDatabase.USERNAME),
            password=os.environ["AKBAR_DB_PASSWORD"],
            database=os.getenv("AKBAR_DB_NAME", DDatabase.DB_NAME),
            charset="utf8mb4",
            autocommit=True,
            cursorclass=DictCursor,
        )

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
                CREATE TABLE IF NOT EXISTS experiment_seed_sequence (
                    sequence_name VARCHAR(32) PRIMARY KEY,
                    next_seed BIGINT UNSIGNED NOT NULL
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
            cursor.execute(
                """
                INSERT IGNORE INTO experiment_seed_sequence
                    (sequence_name, next_seed)
                VALUES ('default', %s)
                """,
                (DExperiment.DEFAULT_SEED,),
            )
            cursor.execute(
                """
                SELECT MAX(
                    CAST(
                        JSON_UNQUOTE(JSON_EXTRACT(config_json, '$.seed'))
                        AS UNSIGNED
                    )
                ) AS maximum_seed
                FROM experiments
                WHERE JSON_EXTRACT(config_json, '$.seed') IS NOT NULL
                """
            )
            row = cursor.fetchone()
            if row["maximum_seed"] is not None:
                cursor.execute(
                    """
                    UPDATE experiment_seed_sequence
                    SET next_seed = GREATEST(next_seed, %s)
                    WHERE sequence_name = 'default'
                    """,
                    (int(row["maximum_seed"]) + 1,),
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

    def allocate_seed(self) -> int:
        with self._connect() as connection, connection.cursor() as cursor:
            connection.begin()
            try:
                cursor.execute(
                    """
                    SELECT next_seed
                    FROM experiment_seed_sequence
                    WHERE sequence_name = 'default'
                    FOR UPDATE
                    """
                )
                row = cursor.fetchone()
                if row is None:
                    raise RuntimeError("experiment seed sequence is not initialized")
                seed = int(row["next_seed"])
                cursor.execute(
                    """
                    UPDATE experiment_seed_sequence
                    SET next_seed = next_seed + 1
                    WHERE sequence_name = 'default'
                    """
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return seed

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
