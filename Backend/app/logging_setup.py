"""Safe, append-only structured logs for ChargePin operations.

One line in a log file is one JSON event.  The logs intentionally contain
operational metadata only: request IDs, agent decisions, retry counts, and
error categories.  Chat text, credentials, authorization values, and provider
payloads are dropped before a record reaches disk.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from threading import RLock
from typing import Any


_WRITE_LOCK = RLock()
_SECRET_KEY_PARTS = (
    "token", "secret", "password", "authorization", "service_key", "api_key",
    "raw_input", "message", "prompt", "query", "content",
)
_MAX_STRING_LENGTH = 240


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_directory() -> Path:
    """Use the mounted Docker directory, or the repository's ``logs`` folder."""
    configured = os.environ.get("CHARGEPIN_LOG_DIR", "").strip()
    if configured:
        return Path(configured)
    # Local test/run: <repo>/Backend/app/logging_setup.py -> <repo>/logs
    return Path(__file__).resolve().parents[2] / "logs"


def _unsafe_key(key: object) -> bool:
    normalized = str(key).casefold()
    return any(part in normalized for part in _SECRET_KEY_PARTS)


def _safe_value(value: Any, *, key: object | None = None) -> Any:
    """Remove sensitive fields and keep log records bounded and JSON-safe."""
    if key is not None and _unsafe_key(key):
        return None
    if isinstance(value, dict):
        return {
            str(item_key): cleaned
            for item_key, item_value in value.items()
            if not _unsafe_key(item_key)
            if (cleaned := _safe_value(item_value, key=item_key)) is not None
        }
    if isinstance(value, (list, tuple, set)):
        return [cleaned for item in value if (cleaned := _safe_value(item)) is not None]
    if isinstance(value, str):
        return value[:_MAX_STRING_LENGTH]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:_MAX_STRING_LENGTH]


def safe_operation_record(event: dict[str, Any], *, level: str = "INFO") -> dict[str, Any] | None:
    """Build the single, safe event shape shared by logs and PostgreSQL."""
    occurred_at = event.get("occurred_at") if isinstance(event.get("occurred_at"), str) else _utc_now()
    clean_event = _safe_value(event)
    if not isinstance(clean_event, dict):
        return None
    clean_event.pop("occurred_at", None)
    return {
        "timestamp_utc": occurred_at,
        "level": level,
        **clean_event,
    }


def append_operation_log(event: dict[str, Any], *, level: str = "INFO") -> dict[str, Any] | None:
    """Append one safe JSON event and return it for optional DB persistence.

    A log write failure must never stop a search.  Returning the already
    sanitised record lets the caller use the same privacy policy for both
    storage targets.
    """
    record = safe_operation_record(event, level=level)
    if record is None:
        return None
    try:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        log_dir = _log_directory()
        with _WRITE_LOCK:
            log_dir.mkdir(parents=True, exist_ok=True)
            with (log_dir / "service.log").open("a", encoding="utf-8") as service_log:
                service_log.write(line)
            if level == "ERROR":
                with (log_dir / "errors.log").open("a", encoding="utf-8") as error_log:
                    error_log.write(line)
    except (OSError, TypeError, ValueError):
        # Logs are evidence, never a reason for the user request itself to fail.
        pass
    return record


def read_recent_operation_logs(limit: int = 30) -> list[dict[str, Any]]:
    """Return bounded, valid, already-sanitised service log records for ops UI."""
    safe_limit = max(1, min(int(limit), 200))
    try:
        lines = (_log_directory() / "service.log").read_text(encoding="utf-8").splitlines()[-safe_limit * 3:]
    except (OSError, UnicodeError):
        return []

    records: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        clean = _safe_value(value)
        if not isinstance(clean, dict):
            continue
        if not isinstance(clean.get("timestamp_utc"), str) or not isinstance(clean.get("event_type"), str):
            continue
        records.append(clean)
    return list(reversed(records[-safe_limit:]))
