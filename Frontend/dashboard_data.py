"""Session-scoped, privacy-preserving summaries for the operations dashboard."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

KST = timezone(timedelta(hours=9))
SEARCH_TYPES = {"직접 검색", "챗 검색"}


def can_view_dashboard(role: str | None) -> bool:
    return role in ("하급 관리자", "상급 관리자")


def can_manage_roles(role: str | None) -> bool:
    return role == "상급 관리자"


def allowed_demo_role_transitions(actor: str | None, current_role: str, *, is_self: bool = False) -> list[str]:
    """Return only PRD-permitted transitions for explicitly fictional demo targets."""
    if not can_manage_roles(actor) or is_self:
        return []
    return {
        "일반 이용자": ["하급 관리자", "상급 관리자"],
        "하급 관리자": ["일반 이용자"],
    }.get(current_role, [])


def event_kind(path: str) -> str | None:
    if path == "/places/suggest":
        return "장소 조회"
    if path == "/chat/plan":
        return "챗 해석"
    if path == "/search":
        return "직접 검색"
    if path.startswith("/search/") and path.endswith("/confirm"):
        return "챗 검색"
    return None


def event_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(KST)


def event_state(event: dict[str, Any]) -> str:
    if event.get("guardrail_blocked"):
        return "차단"
    if event.get("outcome") == "error":
        return "실패"
    if event.get("search_status") == "degraded":
        return "부분 응답"
    if event.get("outcome") == "success":
        return "응답"
    return "확인 필요"


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize only observable current-session client requests.

    Each confirm is counted as one search; planning and place suggestions are
    separate request types. A successful HTTP response is not a provider-health
    or agent-step success.
    """
    observed = []
    for event in events[-100:]:
        kind = event_kind(str(event.get("path") or ""))
        when = event_time(event.get("observed_at"))
        if not kind or when is None:
            continue
        elapsed = event.get("elapsed_ms")
        if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or elapsed < 0:
            elapsed = None
        request_id = event.get("request_id")
        if not (isinstance(request_id, str) and 0 < len(request_id) <= 80 and request_id.isascii()
                and all(char.isalnum() or char in "-_" for char in request_id)):
            request_id = None
        observed.append({"time": when, "kind": kind, "state": event_state(event),
                         "elapsed_ms": elapsed, "request_id": request_id})
    searches = [item for item in observed if item["kind"] in SEARCH_TYPES]
    valid_durations = [item["elapsed_ms"] for item in searches if item["elapsed_ms"] is not None]
    minute_counts = Counter(item["time"].replace(second=0, microsecond=0) for item in searches)
    kind_counts = Counter(item["kind"] for item in observed)
    return {
        "observed": observed,
        "searches": searches,
        "search_count": len(searches),
        "partial_count": sum(item["state"] == "부분 응답" for item in searches),
        "failure_count": sum(item["state"] == "실패" for item in searches),
        "guardrail_block_count": sum(item["state"] == "차단" for item in observed),
        "average_ms": round(mean(valid_durations)) if valid_durations else None,
        "minute_counts": [{"time": key.isoformat(), "count": value} for key, value in sorted(minute_counts.items())],
        "kind_counts": [{"kind": key, "count": kind_counts[key]} for key in
                        ("장소 조회", "챗 해석", "직접 검색", "챗 검색") if kind_counts[key]],
    }


def display_time(value: datetime | None, full: bool = False) -> str:
    if value is None:
        return "확인 필요"
    return value.astimezone(KST).strftime("%m.%d %H:%M:%S" if full else "%H:%M:%S")
