"""Optional PostgreSQL persistence for safe ChargePin operational events.

This module deliberately stores no request text, provider payload, password,
token, or API key.  It is an operational/audit history, not a chat history.
When PostgreSQL is unavailable, callers keep serving requests and file logs
remain the evidence fallback.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from typing import Any
from urllib.parse import quote

try:  # Import remains optional for direct source inspection without deps.
    import psycopg
except ImportError:  # pragma: no cover - exercised only before dependencies install
    psycopg = None  # type: ignore[assignment]


_EVENT_COLUMNS = {"timestamp_utc", "occurred_at", "request_id", "event_type", "status", "level"}


class PostgresOperationStore:
    """Best-effort, reconnecting store for dashboard-safe operational events."""

    def __init__(self) -> None:
        self.enabled = os.environ.get("CHARGEPIN_DATABASE_ENABLED", "false").casefold() == "true"
        self.available = False
        self.last_error: str | None = None
        self.last_checked_at: str | None = None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _dsn(self) -> str | None:
        configured = os.environ.get("DATABASE_URL", "").strip()
        if configured:
            return configured
        host = os.environ.get("POSTGRES_HOST", "").strip()
        database = os.environ.get("POSTGRES_DB", "").strip()
        username = os.environ.get("POSTGRES_USER", "").strip()
        password = os.environ.get("POSTGRES_PASSWORD", "")
        if not all((host, database, username, password)):
            return None
        port = os.environ.get("POSTGRES_PORT", "5432").strip() or "5432"
        return "postgresql://{}:{}@{}:{}/{}".format(
            quote(username, safe=""), quote(password, safe=""), host, quote(port, safe=""), quote(database, safe="")
        )

    def _mark_failure(self, category: str) -> None:
        self.available = False
        self.last_error = category
        self.last_checked_at = self._now()

    def _connect(self) -> Any | None:
        if not self.enabled:
            self.last_error = None
            return None
        dsn = self._dsn()
        if psycopg is None:
            self._mark_failure("driver_unavailable")
            return None
        if not dsn:
            self._mark_failure("configuration_missing")
            return None
        try:
            connection = psycopg.connect(dsn, autocommit=True, connect_timeout=1)
            self.available = True
            self.last_error = None
            self.last_checked_at = self._now()
            return connection
        except Exception:  # Provider connection details must not reach user logs/UI.
            self._mark_failure("connection_unavailable")
            return None

    @staticmethod
    def _ensure_schema(connection: Any) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_events (
                id BIGSERIAL PRIMARY KEY,
                occurred_at TIMESTAMPTZ NOT NULL,
                request_id VARCHAR(80),
                event_type VARCHAR(64) NOT NULL,
                status VARCHAR(32) NOT NULL,
                level VARCHAR(16) NOT NULL,
                details JSONB NOT NULL DEFAULT '{}'::jsonb
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_operation_events_occurred_at ON operation_events (occurred_at DESC)"
        )

    def record(self, record: dict[str, Any]) -> bool:
        """Persist one already-sanitised event.  Failure is non-blocking."""
        connection = self._connect()
        if connection is None:
            return False
        try:
            self._ensure_schema(connection)
            timestamp = str(record.get("timestamp_utc") or self._now())
            occurred_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if occurred_at.tzinfo is None:
                occurred_at = occurred_at.replace(tzinfo=timezone.utc)
            details = {key: value for key, value in record.items() if key not in _EVENT_COLUMNS}
            connection.execute(
                """
                INSERT INTO operation_events (occurred_at, request_id, event_type, status, level, details)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    occurred_at,
                    record.get("request_id"),
                    str(record.get("event_type") or "unknown"),
                    str(record.get("status") or "unknown"),
                    str(record.get("level") or "INFO"),
                    json.dumps(details, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            return True
        except Exception:
            self._mark_failure("write_unavailable")
            return False
        finally:
            connection.close()

    def recent(self, limit: int = 50, *, since: datetime | None = None) -> list[dict[str, Any]]:
        """Return newest safe rows.  A DB read failure only returns an empty list."""
        safe_limit = max(1, min(int(limit), 200))
        connection = self._connect()
        if connection is None:
            return []
        try:
            self._ensure_schema(connection)
            if since is None:
                statement = """
                    SELECT occurred_at, request_id, event_type, status, level, details
                    FROM operation_events ORDER BY id DESC LIMIT %s
                """
                parameters = (safe_limit,)
            else:
                statement = """
                    SELECT occurred_at, request_id, event_type, status, level, details
                    FROM operation_events WHERE occurred_at >= %s ORDER BY id DESC LIMIT %s
                """
                parameters = (since, safe_limit)
            rows = connection.execute(statement, parameters).fetchall()
            records = []
            for occurred_at, request_id, event_type, status, level, details in rows:
                safe_details = details if isinstance(details, dict) else {}
                records.append({
                    "occurred_at": occurred_at.isoformat(),
                    "request_id": request_id,
                    "event_type": event_type,
                    "status": status,
                    "level": level,
                    **safe_details,
                })
            return records
        except Exception:
            self._mark_failure("read_unavailable")
            return []
        finally:
            connection.close()

    def snapshot(self) -> dict[str, Any]:
        """Status only; never expose DSN or error text."""
        return {
            "enabled": self.enabled,
            "available": self.available if self.enabled else False,
            "last_error": self.last_error,
            "last_checked_at": self.last_checked_at,
        }
