from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class SessionStore:
    """Persist conversation payloads with an automatically refreshed expiry."""

    def __init__(self) -> None:
        self._pool = None
        self._memory: dict[str, tuple[dict[str, Any], datetime]] = {}
        self._lock = threading.RLock()
        self.ttl = timedelta(hours=float(os.getenv("SESSION_TTL_HOURS", "24")))
        if self.ttl <= timedelta(0):
            raise ValueError("SESSION_TTL_HOURS must be greater than zero.")

    @property
    def persistent(self) -> bool:
        return self._pool is not None

    @property
    def pool(self):
        return self._pool

    def open(self) -> None:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            if os.getenv("APP_ENV", "development").lower() == "production":
                raise RuntimeError("DATABASE_URL is required in production.")
            logger.warning(
                "DATABASE_URL is not set; using temporary in-memory sessions. "
                "Set DATABASE_URL to enable Neon Postgres persistence."
            )
            return

        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        dsn = dsn.replace("postgresql+psycopg://", "postgresql://", 1)
        self._pool = ConnectionPool(
            conninfo=dsn,
            min_size=1,
            max_size=int(os.getenv("DATABASE_POOL_SIZE", "3")),
            kwargs={
                "autocommit": True,
                "row_factory": dict_row,
                "prepare_threshold": 0,
                "connect_timeout": 10,
            },
            timeout=10,
            open=False,
        )
        self._pool.open(wait=True)
        with self._pool.connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schemesage_sessions (
                    session_id UUID PRIMARY KEY,
                    payload JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    expires_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS schemesage_sessions_expires_at_idx "
                "ON schemesage_sessions (expires_at)"
            )

    def close(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None

    def ping(self) -> bool:
        if self._pool is None:
            return True
        with self._pool.connection() as connection:
            connection.execute("SELECT 1").fetchone()
        return True

    def create(self, session_id: str, payload: dict[str, Any]) -> None:
        from psycopg.types.json import Jsonb

        expiry = datetime.now(timezone.utc) + self.ttl
        if self._pool is None:
            with self._lock:
                self._memory[session_id] = (payload, expiry)
            return

        with self._pool.connection() as connection:
            connection.execute(
                """
                INSERT INTO schemesage_sessions (session_id, payload, expires_at)
                VALUES (%s, %s, %s)
                """,
                (session_id, Jsonb(payload), expiry),
            )

    def get(self, session_id: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        if self._pool is None:
            with self._lock:
                record = self._memory.get(session_id)
                if record is None:
                    return None
                if record[1] <= now:
                    self._memory.pop(session_id, None)
                    return None
                self._memory[session_id] = (record[0], now + self.ttl)
                return dict(record[0])

        with self._pool.connection() as connection:
            row = connection.execute(
                """
                UPDATE schemesage_sessions
                SET updated_at = now(), expires_at = %s
                WHERE session_id = %s AND expires_at > now()
                RETURNING payload
                """,
                (now + self.ttl, session_id),
            ).fetchone()
            return dict(row["payload"]) if row else None

    def save(self, session_id: str, payload: dict[str, Any]) -> None:
        expiry = datetime.now(timezone.utc) + self.ttl
        if self._pool is None:
            with self._lock:
                if session_id in self._memory:
                    self._memory[session_id] = (payload, expiry)
            return

        from psycopg.types.json import Jsonb

        with self._pool.connection() as connection:
            connection.execute(
                """
                UPDATE schemesage_sessions
                SET payload = %s, updated_at = now(), expires_at = %s
                WHERE session_id = %s
                """,
                (Jsonb(payload), expiry, session_id),
            )

    def delete(self, session_id: str) -> None:
        if self._pool is None:
            with self._lock:
                self._memory.pop(session_id, None)
            return
        with self._pool.connection() as connection:
            connection.execute(
                "DELETE FROM schemesage_sessions WHERE session_id = %s",
                (session_id,),
            )

    def purge_expired(self) -> list[str]:
        if self._pool is None:
            now = datetime.now(timezone.utc)
            with self._lock:
                expired = [
                    session_id
                    for session_id, (_, expiry) in self._memory.items()
                    if expiry <= now
                ]
                for session_id in expired:
                    self._memory.pop(session_id, None)
                return expired

        with self._pool.connection() as connection:
            rows = connection.execute(
                """
                DELETE FROM schemesage_sessions
                WHERE expires_at <= now()
                RETURNING session_id::text
                """
            ).fetchall()
            return [row["session_id"] for row in rows]
