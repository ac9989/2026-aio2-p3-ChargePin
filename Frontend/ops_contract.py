"""Data contracts for server-side operations panels (platform and Auto Healing).

The dashboard renders these panels as "연결 대기" until the backend serves the
payloads below. Normalizers accept only the documented fields, drop anything
else (secret values, free text), and never invent missing numbers.

GET /api/v1/ops/platform  (operator only)
    {"source": "kubernetes" | "compose", "observed_at": ISO-8601,
     "namespace": "chargepin",
     "workloads": [{"kind": "Deployment", "name": "chargepin-backend", "desired": 1, "ready": 1,
                    "image": "ghcr.io/ac9989/chargepin-backend:sha-...", "restarts": 0,
                    "liveness": "/healthz", "readiness": "/healthz"}],
     "services":  [{"name": "chargepin-backend", "type": "ClusterIP", "port": 8000, "endpoints": 1}],
     "config":    [{"kind": "Secret", "name": "chargepin-secrets", "keys": 6},
                   {"kind": "ConfigMap", "name": "chargepin-config", "keys": 5}]}

GET /api/v1/ops/healing  (operator only) — ops/autoheal.py policy + JSONL events
    {"policy": {"mode": "apply" | "dry-run", "consecutive_unhealthy": 2, "cooldown_seconds": 120,
                "window_seconds": 600, "max_restarts": 3, "recovery_timeout_seconds": 120,
                "scope": ["chargepin_repo-frontend-1"]},
     "events": [{"timestamp_utc": ISO-8601, "event": "restart_attempt" | "recovered" | "recovery_timeout"
                 | "restart_failed" | "state_changed" | "recovery_interrupted",
                 "container": "...", "duration_seconds": 8.48}]}
"""
from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

# Defaults written in ops/autoheal.py (Watcher.__init__). Shown as "코드 기준" until the server reports its policy.
CODE_HEALING_POLICY = {
    "mode": "dry-run (기본) · --apply 시 재시작",
    "consecutive_unhealthy": 2,
    "cooldown_seconds": 120,
    "window_seconds": 600,
    "max_restarts": 3,
    "recovery_timeout_seconds": 120,
    "scope": ["chargepin_repo-frontend-1"],
}
EXPECTED_RESOURCES = [
    ("Deployment", "chargepin-backend", "/healthz 생존 · 준비 프로브"),
    ("Deployment", "chargepin-frontend", "/_stcore/health 생존 · 준비 프로브"),
    ("Service", "chargepin-backend", "프론트가 서비스 이름으로 백엔드 탐색"),
    ("Service", "chargepin-frontend", "외부 접속 · 로드밸런싱"),
    ("ConfigMap", "chargepin-config", "모델명 · 캐시 TTL · 지연 기준"),
    ("Secret", "chargepin-secrets", "API 키 · 서비스 키 (값은 표시하지 않음)"),
]
HEALING_EVENTS = {"restart_attempt", "recovered", "recovery_timeout", "restart_failed",
                  "state_changed", "recovery_interrupted"}
WORKLOAD_KINDS = {"Deployment", "StatefulSet", "DaemonSet", "Pod", "ComposeService"}
CONFIG_KINDS = {"Secret", "ConfigMap"}


def _count(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _text(value: Any, limit: int = 120) -> str | None:
    return value[:limit] if isinstance(value, str) and value.strip() else None


def _time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def normalize_platform(payload: Any) -> dict[str, Any] | None:
    """Return a safe platform view, or None when the payload is missing or malformed."""
    if not isinstance(payload, dict) or payload.get("source") not in ("kubernetes", "compose"):
        return None
    workloads = []
    for item in payload.get("workloads") or []:
        if not isinstance(item, dict) or item.get("kind") not in WORKLOAD_KINDS or not _text(item.get("name")):
            continue
        workloads.append({
            "kind": item["kind"], "name": _text(item["name"]), "desired": _count(item.get("desired")),
            "ready": _count(item.get("ready")), "restarts": _count(item.get("restarts")),
            "image": _text(item.get("image"), 160), "liveness": _text(item.get("liveness"), 60),
            "readiness": _text(item.get("readiness"), 60),
        })
    services = []
    for item in payload.get("services") or []:
        if isinstance(item, dict) and _text(item.get("name")):
            services.append({"name": _text(item["name"]), "type": _text(item.get("type"), 30),
                             "port": _count(item.get("port")), "endpoints": _count(item.get("endpoints"))})
    config = []
    for item in payload.get("config") or []:
        # Only the kind, name and key count are kept: values never reach the dashboard.
        if isinstance(item, dict) and item.get("kind") in CONFIG_KINDS and _text(item.get("name")):
            config.append({"kind": item["kind"], "name": _text(item["name"]), "keys": _count(item.get("keys"))})
    return {"source": payload["source"], "observed_at": _time(payload.get("observed_at")),
            "namespace": _text(payload.get("namespace"), 60), "workloads": workloads,
            "services": services, "config": config}


def platform_ready(platform: dict[str, Any] | None) -> bool:
    """True only when every reported workload has all desired replicas ready."""
    if not platform or not platform["workloads"]:
        return False
    return all(item["desired"] is not None and item["ready"] is not None and item["desired"] > 0
               and item["ready"] >= item["desired"] for item in platform["workloads"])


def normalize_healing(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    raw_policy = payload.get("policy") if isinstance(payload.get("policy"), dict) else {}
    policy = {key: _count(raw_policy.get(key)) for key in
              ("consecutive_unhealthy", "cooldown_seconds", "window_seconds", "max_restarts", "recovery_timeout_seconds")}
    policy["mode"] = raw_policy.get("mode") if raw_policy.get("mode") in ("apply", "dry-run") else None
    scope = raw_policy.get("scope")
    policy["scope"] = [_text(item, 80) for item in scope if _text(item, 80)] if isinstance(scope, list) else []
    events = []
    for item in payload.get("events") or []:
        if not isinstance(item, dict) or item.get("event") not in HEALING_EVENTS:
            continue
        when = _time(item.get("timestamp_utc"))
        if when is None:
            continue
        duration = item.get("duration_seconds")
        duration = float(duration) if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration >= 0 else None
        events.append({"time": when, "event": item["event"], "container": _text(item.get("container"), 80),
                       "duration_seconds": duration})
    events.sort(key=lambda item: item["time"])
    return {"policy": policy, "events": events[-200:]}


def healing_stats(healing: dict[str, Any] | None) -> dict[str, Any]:
    """Auto-recovery ratio = recovered / restart attempts, from recorded events only."""
    if not healing:
        return {"attempts": 0, "recovered": 0, "timeouts": 0, "failed": 0, "rate": None, "average_seconds": None}
    events = healing["events"]
    attempts = sum(item["event"] == "restart_attempt" for item in events)
    recovered = [item for item in events if item["event"] == "recovered"]
    durations = [item["duration_seconds"] for item in recovered if item["duration_seconds"] is not None]
    return {
        "attempts": attempts, "recovered": len(recovered),
        "timeouts": sum(item["event"] == "recovery_timeout" for item in events),
        "failed": sum(item["event"] == "restart_failed" for item in events),
        "rate": round(min(len(recovered), attempts) / attempts * 100, 1) if attempts else None,
        "average_seconds": round(mean(durations), 2) if durations else None,
    }
