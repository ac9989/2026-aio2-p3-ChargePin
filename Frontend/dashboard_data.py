"""Session-scoped, privacy-preserving summaries for the operations dashboard.

Calculation only: no Streamlit imports. Every summary states what it can prove
(current-session client observations, code-level controls, management-sheet
records) and never invents server-wide values.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any

KST = timezone(timedelta(hours=9))
SEARCH_TYPES = {"직접 검색", "챗 검색"}

PLAN_STATUS_LABELS = {
    "AWAITING_CONFIRMATION": "조건 확인 대기",
    "AWAITING_LOCATION_CONFIRMATION": "위치 확인 대기",
    "NEEDS_INPUT": "추가 입력 요청",
    "BLOCKED": "가드레일 차단",
}
AVAILABILITY_LABELS = {
    "AVAILABLE": "충전 가능",
    "DELAYED": "정보 지연",
    "UNAVAILABLE": "확인 불가",
    "CANDIDATE_ONLY": "후보만 확인",
}
ERROR_CLASSES = ("요청 측 4xx", "서버 측 5xx", "연결 실패")
COMPLIANCE_STATUSES = ("충족", "구현", "부분", "미착수")


def can_view_dashboard(role: str | None) -> bool:
    return role in ("하급 관리자", "상급 관리자")


def can_manage_roles(role: str | None) -> bool:
    return role == "상급 관리자"


def can_export_report(role: str | None) -> bool:
    """Compliance report export follows the same boundary as role management."""
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
    if event.get("outcome") == "error":
        return "실패"
    if event.get("plan_status") == "BLOCKED":
        return "차단"
    if event.get("search_status") == "degraded":
        return "부분 응답"
    if event.get("outcome") == "success":
        return "응답"
    return "확인 필요"


def error_class(event: dict[str, Any]) -> str | None:
    """Separate client-side request errors from server-side and transport failures."""
    if event.get("outcome") != "error":
        return None
    code = event.get("status_code")
    if isinstance(code, int) and not isinstance(code, bool):
        if 400 <= code < 500:
            return "요청 측 4xx"
        if code >= 500:
            return "서버 측 5xx"
    return "연결 실패"


def _safe_count(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _safe_request_id(value: Any) -> str | None:
    if (isinstance(value, str) and 0 < len(value) <= 80 and value.isascii()
            and all(char.isalnum() or char in "-_" for char in value)):
        return value
    return None


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
        plan_status = event.get("plan_status") if event.get("plan_status") in PLAN_STATUS_LABELS else None
        critic = event.get("critic_decision") if event.get("critic_decision") in ("PASS", "SAFE_UNAVAILABLE") else None
        raw_availability = event.get("availability_counts")
        availability = ({key: _safe_count(value) for key, value in raw_availability.items()
                         if key in AVAILABILITY_LABELS} if isinstance(raw_availability, dict) else {})
        code = event.get("status_code")
        observed.append({
            "time": when, "kind": kind, "state": event_state(event),
            "elapsed_ms": elapsed, "request_id": _safe_request_id(event.get("request_id")),
            "status_code": code if isinstance(code, int) and not isinstance(code, bool) else None,
            "error_class": error_class(event), "plan_status": plan_status,
            "critic_decision": critic, "availability": availability,
            "finding_count": _safe_count(event.get("critic_finding_count")),
        })
    searches = [item for item in observed if item["kind"] in SEARCH_TYPES]
    valid_durations = [item["elapsed_ms"] for item in searches if item["elapsed_ms"] is not None]
    minute_counts = Counter(item["time"].replace(second=0, microsecond=0) for item in searches)
    kind_counts = Counter(item["kind"] for item in observed)
    errors = Counter(item["error_class"] for item in observed if item["error_class"])
    server_side = errors["서버 측 5xx"] + errors["연결 실패"]
    plan_counts = Counter(item["plan_status"] for item in observed if item["plan_status"])
    availability = Counter()
    for item in searches:
        availability.update(item["availability"])
    return {
        "observed": observed,
        "searches": searches,
        "search_count": len(searches),
        "partial_count": sum(item["state"] == "부분 응답" for item in searches),
        "failure_count": sum(item["state"] == "실패" for item in searches),
        "average_ms": round(mean(valid_durations)) if valid_durations else None,
        "minute_counts": [{"time": key.isoformat(), "count": value} for key, value in sorted(minute_counts.items())],
        "kind_counts": [{"kind": key, "count": kind_counts[key]} for key in
                        ("장소 조회", "챗 해석", "직접 검색", "챗 검색") if kind_counts[key]],
        "error_counts": [{"kind": key, "count": errors[key]} for key in ERROR_CLASSES],
        "server_error_count": server_side,
        "server_error_rate": round(server_side / len(observed) * 100, 1) if observed else None,
        "plan_counts": [{"kind": PLAN_STATUS_LABELS[key], "count": plan_counts[key]}
                        for key in PLAN_STATUS_LABELS if plan_counts[key]],
        "availability_counts": [{"kind": AVAILABILITY_LABELS[key], "count": availability[key]}
                                for key in AVAILABILITY_LABELS if availability[key]],
        "traced_count": sum(item["request_id"] is not None for item in observed),
    }


def guardrail_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Policy decisions by layer. Passed decisions are counted, not only blocks."""
    observed = data["observed"]
    plans = [item for item in observed if item["plan_status"]]
    blocked = sum(item["plan_status"] == "BLOCKED" for item in plans)
    judged = [item for item in observed if item["critic_decision"]]
    safe = sum(item["critic_decision"] == "SAFE_UNAVAILABLE" for item in judged)
    denied = sum(item["status_code"] in (401, 403) for item in observed)
    findings = sum(item["finding_count"] for item in judged)
    return {
        "input_checked": len(plans), "input_blocked": blocked, "input_passed": len(plans) - blocked,
        "output_checked": len(judged), "output_safe": safe, "output_pass": len(judged) - safe,
        "access_denied": denied, "finding_count": findings,
    }


def health_label(payload: dict[str, Any] | None, reachable: bool) -> str:
    """Map /healthz to ok · degraded · down without upgrading an unknown reply."""
    if not reachable:
        return "중단"
    status = (payload or {}).get("status")
    if status == "ok":
        return "정상"
    if status == "degraded":
        return "저하"
    return "확인 필요"


def load_compliance_reference(path: Path | None = None) -> dict[str, Any]:
    source = path or Path(__file__).with_name("compliance_reference.json")
    return json.loads(source.read_text(encoding="utf-8"))


def evaluate_compliance(reference: dict[str, Any], live: dict[str, Any]) -> list[dict[str, Any]]:
    """Overlay live evidence on recorded controls.

    A live signal can only promote an implemented control ("구현") to "충족"
    because it is execution evidence. It never upgrades partial or missing work.
    """
    signals = {
        "health": live.get("health") == "정상",
        "guardrail_session": _safe_count(live.get("input_blocked")) > 0,
        "critic_session": _safe_count(live.get("output_checked")) > 0,
        "trace_session": _safe_count(live.get("traced_count")) > 0,
        "ci_tests": live.get("ci_tests") == "성공",
        "k8s_ready": live.get("k8s_ready") is True,
        "healing": _safe_count((live.get("healing") or {}).get("recovered")) > 0,
    }
    notes = {
        "health": "실시간 /healthz 정상 응답",
        "guardrail_session": f'현재 세션 입력 차단 {_safe_count(live.get("input_blocked"))}건 관측',
        "critic_session": f'현재 세션 Critic 판정 {_safe_count(live.get("output_checked"))}건 관측',
        "trace_session": f'현재 세션 요청 ID {_safe_count(live.get("traced_count"))}건 추적',
        "ci_tests": "최근 CI 테스트 작업 성공 (GitHub Actions)",
        "k8s_ready": "클러스터 워크로드 전체 준비 완료 (서버 보고)",
        "healing": "힐링 이벤트 복구 {0}건 / 재시작 {1}건 (서버 보고)".format(
            _safe_count((live.get("healing") or {}).get("recovered")),
            _safe_count((live.get("healing") or {}).get("attempts"))),
    }
    items = []
    for item in reference.get("items", []):
        status = item.get("status") if item.get("status") in COMPLIANCE_STATUSES else "미착수"
        evidence = str(item.get("evidence", ""))
        key = item.get("live")
        live_note = ""
        if key in signals and signals[key]:
            live_note = notes[key]
            if status == "구현":
                status = "충족"
        items.append({**item, "status": status, "evidence": evidence, "live_note": live_note})
    return items


def compliance_score(items: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(item["status"] for item in items)
    return {"total": len(items), "met": counts["충족"],
            "counts": [{"kind": key, "count": counts[key]} for key in COMPLIANCE_STATUSES]}


def action_items(items: list[dict[str, Any]], data: dict[str, Any], health: str,
                 limit: int = 5) -> list[dict[str, str]]:
    """Live problems first, then recorded gaps ordered by severity."""
    actions: list[dict[str, str]] = []
    if health != "정상":
        actions.append({"level": "bad", "title": "백엔드 헬스 체크 " + health,
                        "detail": "/healthz 응답 확인 · 실시간", "ref": "R-3"})
    if data.get("server_error_count"):
        actions.append({"level": "bad", "title": f'서버 측 오류 {data["server_error_count"]}건',
                        "detail": "현재 세션 · 5xx 또는 연결 실패", "ref": "R-4"})
    order = {"미착수": 0, "부분": 1}
    gaps = sorted((item for item in items if item["status"] in order),
                  key=lambda item: (order[item["status"]], item.get("id", "")))
    for item in gaps:
        actions.append({"level": "warn" if item["status"] == "부분" else "muted",
                        "title": str(item.get("control_title", item.get("id", ""))),
                        "detail": item["status"] + " · " + str(item.get("evidence", "")),
                        "ref": str(item.get("id", ""))})
    return actions[:limit]


def compliance_rows(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{
        "ID": str(item.get("id", "")), "영역": str(item.get("area", "")),
        "점검 항목": str(item.get("control_title", "")), "통제 내용": str(item.get("control", "")),
        "판정": item["status"],
        "근거": item["evidence"] + (" · " + item["live_note"] if item["live_note"] else ""),
        "출처": str(item.get("source", "")),
    } for item in items]


def display_time(value: datetime | None, full: bool = False) -> str:
    if value is None:
        return "확인 필요"
    return value.astimezone(KST).strftime("%m.%d %H:%M:%S" if full else "%H:%M:%S")
