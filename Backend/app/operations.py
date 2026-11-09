"""Read-only Docker Compose operational snapshots for the administrator dashboard."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


_HEALING_EVENTS = {
    "restart_attempt", "recovered", "recovery_timeout", "restart_failed",
    "state_changed", "recovery_interrupted",
}
_RUNTIME_CONFIG_NAMES = (
    "OPENAI_PLANNER_MODEL", "KECO_INFO_CACHE_TTL_SECONDS",
    "KECO_STATUS_CACHE_TTL_SECONDS", "CHARGER_FRESHNESS_MINUTES",
    "CHARGEPIN_ENABLE_TEST_SCENARIOS",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _healthy(url: str) -> bool:
    """Check an internal service endpoint without returning upstream content."""
    try:
        with urlopen(url, timeout=2) as response:
            return 200 <= response.status < 400
    except (URLError, TimeoutError, ValueError):
        return False


def _env_nonnegative_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.environ.get(name, str(default))))
    except ValueError:
        return default


def compose_platform_snapshot() -> dict[str, Any]:
    """Report only observed Compose service availability, never Docker socket data."""
    frontend_url = os.environ.get(
        "CHARGEPIN_FRONTEND_HEALTH_URL", "http://frontend:8501/_stcore/health"
    )
    frontend_ready = int(_healthy(frontend_url))
    configured_runtime_keys = sum(bool(os.environ.get(name)) for name in _RUNTIME_CONFIG_NAMES)
    return {
        "source": "compose",
        "observed_at": _utc_now(),
        "namespace": os.environ.get("COMPOSE_PROJECT_NAME", "docker-compose"),
        "workloads": [
            {
                "kind": "ComposeService", "name": "backend", "desired": 1, "ready": 1,
                "restarts": None, "image": os.environ.get("CHARGEPIN_BACKEND_IMAGE") or None,
                "liveness": "/healthz", "readiness": "/healthz",
            },
            {
                "kind": "ComposeService", "name": "frontend", "desired": 1, "ready": frontend_ready,
                "restarts": None, "image": os.environ.get("CHARGEPIN_FRONTEND_IMAGE") or None,
                "liveness": "/_stcore/health", "readiness": "/_stcore/health",
            },
        ],
        "services": [
            {"name": "backend", "type": "Compose network", "port": 8000, "endpoints": 1},
            {"name": "frontend", "type": "Compose network", "port": 8501, "endpoints": frontend_ready},
        ],
        "config": [
            {
                "kind": "RuntimeConfig", "name": "backend runtime configuration",
                "keys": configured_runtime_keys,
            },
        ],
    }


def healing_snapshot() -> dict[str, Any]:
    """Parse safe, bounded Auto Healing events from a read-only JSONL log."""
    mode = os.environ.get("AUTOHEAL_MODE", "dry-run").strip().lower()
    mode = mode if mode in {"apply", "dry-run"} else "dry-run"
    policy = {
        "mode": mode,
        "consecutive_unhealthy": _env_nonnegative_int("AUTOHEAL_CONSECUTIVE_UNHEALTHY", 2),
        "cooldown_seconds": _env_nonnegative_int("AUTOHEAL_COOLDOWN_SECONDS", 120),
        "window_seconds": _env_nonnegative_int("AUTOHEAL_WINDOW_SECONDS", 600),
        "max_restarts": _env_nonnegative_int("AUTOHEAL_MAX_RESTARTS", 3),
        "recovery_timeout_seconds": _env_nonnegative_int("AUTOHEAL_RECOVERY_TIMEOUT_SECONDS", 120),
        "scope": [item.strip() for item in os.environ.get("AUTOHEAL_SCOPE", "").split(",") if item.strip()],
    }
    path_value = os.environ.get("AUTOHEAL_LOG_PATH", "").strip()
    if not path_value:
        return {"policy": policy, "events": []}

    try:
        lines = Path(path_value).read_text(encoding="utf-8").splitlines()[-200:]
    except (OSError, UnicodeError):
        return {"policy": policy, "events": []}

    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            item = json.loads(line)
            event = item.get("event")
            timestamp = item.get("timestamp_utc")
            container = item.get("container")
            if event not in _HEALING_EVENTS or not isinstance(timestamp, str) or not isinstance(container, str):
                continue
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            record: dict[str, Any] = {
                "timestamp_utc": timestamp,
                "event": event,
                "container": container[:80],
            }
            duration = item.get("duration_seconds")
            if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration >= 0:
                record["duration_seconds"] = round(float(duration), 2)
            events.append(record)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return {"policy": policy, "events": events[-200:]}
