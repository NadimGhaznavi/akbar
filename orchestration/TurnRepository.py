"""Durable MariaDB work queue shared by independent orchestration processes."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import uuid4

from database.Database import connect


class TurnRepository(Protocol):
    def initialize(self) -> None: ...
    def mark_interrupted(self) -> None: ...
    def enqueue(self, prompt: str, source: str) -> str | None: ...
    def claim_next(self) -> dict[str, Any] | None: ...
    def finish(
        self,
        turn_id: str,
        status: str,
        response: str | None = None,
        error: str | None = None,
    ) -> None: ...


class MariaDBTurnRepository:
    def initialize(self) -> None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_turn_gate (
                    gate_name VARCHAR(32) PRIMARY KEY
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                INSERT IGNORE INTO agent_turn_gate (gate_name)
                VALUES ('default')
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_turns (
                    turn_id CHAR(36) PRIMARY KEY,
                    source VARCHAR(32) NOT NULL,
                    prompt TEXT NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    response_text LONGTEXT NULL,
                    error_text TEXT NULL,
                    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    started_at DATETIME(6) NULL,
                    completed_at DATETIME(6) NULL,
                    INDEX idx_agent_turns_status_created (status, created_at)
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )

    def mark_interrupted(self) -> None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE agent_turns
                SET status = 'interrupted', completed_at = CURRENT_TIMESTAMP(6),
                    error_text = 'Agent worker restarted during execution'
                WHERE status = 'running'
                """
            )

    def enqueue(self, prompt: str, source: str) -> str | None:
        turn_id = str(uuid4())
        with connect() as connection, connection.cursor() as cursor:
            connection.begin()
            try:
                cursor.execute(
                    """
                    SELECT gate_name FROM agent_turn_gate
                    WHERE gate_name = 'default'
                    FOR UPDATE
                    """
                )
                cursor.fetchone()
                cursor.execute(
                    """
                    SELECT turn_id FROM agent_turns
                    WHERE status IN ('queued', 'running')
                    LIMIT 1
                    """
                )
                if cursor.fetchone() is not None:
                    connection.rollback()
                    return None
                cursor.execute(
                    """
                    INSERT INTO agent_turns (turn_id, source, prompt, status)
                    VALUES (%s, %s, %s, 'queued')
                    """,
                    (turn_id, source, prompt),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return turn_id

    def claim_next(self) -> dict[str, Any] | None:
        with connect() as connection, connection.cursor() as cursor:
            connection.begin()
            try:
                cursor.execute(
                    """
                    SELECT turn_id, source, prompt
                    FROM agent_turns
                    WHERE status = 'queued'
                    ORDER BY created_at
                    LIMIT 1
                    FOR UPDATE
                    """
                )
                row = cursor.fetchone()
                if row is None:
                    connection.rollback()
                    return None
                cursor.execute(
                    """
                    UPDATE agent_turns
                    SET status = 'running', started_at = CURRENT_TIMESTAMP(6)
                    WHERE turn_id = %s
                    """,
                    (row["turn_id"],),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return dict(row)

    def finish(
        self,
        turn_id: str,
        status: str,
        response: str | None = None,
        error: str | None = None,
    ) -> None:
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE agent_turns
                SET status = %s, response_text = %s, error_text = %s,
                    completed_at = CURRENT_TIMESTAMP(6)
                WHERE turn_id = %s
                """,
                (status, response, error, turn_id),
            )
