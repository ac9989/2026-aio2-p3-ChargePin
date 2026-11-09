"""ChargePin operations dashboard: agent trace, guardrails, reliability, pipeline, compliance.

Screen code only. Calculations live in dashboard_data.py. Every panel names its
data basis (현재 세션 · 코드 기준 · 관리표 기록 · GitHub 실시간 · 서버 연결 대기).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
from typing import Any, Callable

import altair as alt
import pandas as pd
import requests
import streamlit as st

from api_client import ApiError
from ops_contract import (CODE_HEALING_POLICY, EXPECTED_RESOURCES, healing_stats, normalize_healing,
                          normalize_platform, platform_ready)
from dashboard_data import (
    AVAILABILITY_LABELS, KST, PLAN_STATUS_LABELS, action_items, can_export_report,
    compliance_rows, compliance_score, display_time, evaluate_compliance, event_time, guardrail_summary,
    health_label, load_compliance_reference, summarize_events,
)

AMBER = "#C8940B"
DARK = "#252B32"
MUTED = "#74808C"
GRID = "#EBEEF1"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1REaJ0qNf6k_KcAHylli05kOVM_SWHloR/edit?gid=853363652#gid=853363652"
ACTIONS_URL = "https://github.com/ac9989/2026-aio2-p3-ChargePin/actions"
REPO_API = "https://api.github.com/repos/ac9989/2026-aio2-p3-ChargePin"

MENUS = ["운영 개요", "에이전트 처리", "가드레일", "안정성·힐링", "배포 파이프라인", "컴플라이언스"]
MENU_SCOPES = {
    "운영 개요": "에이전트 처리 · 가드레일 · 복구 · 배포 상태를 한 화면에서 확인",
    "에이전트 처리": "현재 세션 · 최근 100건 · Planner → Executor → Critic",
    "가드레일": "계층별 정책 판정 · 차단과 통과를 함께 기록",
    "안정성·힐링": "헬스 체크 · Auto Healing · 힐링 계층",
    "배포 파이프라인": "GitHub Actions 실시간 · 관리표 기록",
    "컴플라이언스": "평가 기준 대비 자가 점검 · 판정마다 근거와 출처 표기",
}
STATUS_TONES = {"충족": "good", "구현": "neutral", "부분": "warn", "미착수": "bad",
                "성공": "good", "실패": "bad", "진행 중": "warn", "건너뜀": "muted", "수동": "neutral"}


def label(text: Any) -> str:
    return escape(str(text), quote=True)


def section_title(title: str, subtitle: str = "") -> None:
    note = '<span class="cp-section-note">' + label(subtitle) + '</span>' if subtitle else ""
    st.markdown('<div class="cp-section-title"><h3>' + label(title) + '</h3>' + note + '</div>',
                unsafe_allow_html=True)


def empty_chart(message: str = "데이터 연결 대기") -> None:
    st.markdown('<div class="cp-chart-empty"><span class="cp-empty-icon">—</span><span>'
                + label(message) + '</span></div>', unsafe_allow_html=True)


def status_tag(text: str, tone: str | None = None) -> str:
    tone = tone or STATUS_TONES.get(text, "neutral")
    return '<span class="cp-status ' + label(tone) + '">' + label(text) + '</span>'


ICONS = {
    "pulse": '<path d="M3 12h4l2-5 3 10 3-6h6"/>',
    "alert": '<path d="M12 3 3 20h18L12 3zM12 9v5m0 3h.01"/>',
    "shield": '<path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6z"/><path d="m9 12 2 2 4-4"/>',
    "check": '<path d="M8 4h8v3H8zM6 5H4v16h16V5h-4M8 13l2 2 5-5"/>',
    "chat": '<path d="M4 5h16v11H9l-5 4V5z"/><path d="m10 10 2-2 2 2-2 2z"/>',
    "search": '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
    "clock": '<circle cx="12" cy="12" r="8"/><path d="M12 7v5l4 2"/>',
    "judge": '<path d="M12 4v16M5 8h14M7 8l-3 6h6zM17 8l-3 6h6z"/>',
    "lock": '<rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "flag": '<path d="M5 21V4h11l-2 4 2 4H5"/>',
    "heal": '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 9a7 7 0 0 1 12-2l2 5M4 12l2 5a7 7 0 0 0 12-2"/>',
    "branch": '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 6h8m2 2v8"/>',
    "package": '<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9zM4 7.5l8 4.5 8-4.5M12 12v9"/>',
    "server": '<rect x="4" y="5" width="16" height="6" rx="2"/><rect x="4" y="13" width="16" height="6" rx="2"/><path d="M8 8h.01M8 16h.01M12 8h5M12 16h5"/>',
}


def metric_card(title: str, value: str, detail: str, tone: str = "neutral", icon: str = "search") -> None:
    svg = ('<span class="cp-metric-icon"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" '
           'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
           + ICONS.get(icon, ICONS["search"]) + '</svg></span>')
    st.markdown(
        '<div class="cp-metric">' + svg + '<div class="cp-metric-content"><div class="cp-metric-title-row">'
        '<span class="cp-metric-title">' + label(title) + '</span></div><div class="cp-metric-value">'
        + label(value) + '</div><span class="cp-metric-sub ' + label(tone) + '">' + label(detail)
        + '</span></div></div>', unsafe_allow_html=True)


def metric_row(key: str, cards: list[tuple[str, str, str, str, str]]) -> None:
    with st.container(key=key):
        for col, item in zip(st.columns(len(cards), gap="medium"), cards):
            with col:
                metric_card(*item)


def _axis_config(chart: Any) -> Any:
    return chart.configure_view(stroke=None).configure_axis(
        labelColor=MUTED, titleColor=MUTED, gridColor=GRID, domainColor=GRID,
        labelFontSize=13, titleFontSize=13)


def line_chart(data: list[dict[str, Any]], value: str, unit: str, empty: str) -> None:
    if not data:
        empty_chart(empty)
        return
    frame = pd.DataFrame(data)
    frame["label"] = pd.to_datetime(frame["time"], utc=True).dt.tz_convert(KST).dt.strftime("%m.%d %H:%M")
    frame["_order"] = range(len(frame))
    x = alt.X("label:N", title=None, sort=alt.SortField(field="_order", order="ascending"),
              axis=alt.Axis(labelAngle=0, labelLimit=90, labelOverlap=True, tickCount=5))
    axis = alt.Axis(grid=True, tickMinStep=1, format="d") if unit == "건" else alt.Axis(grid=True, format=",.0f")
    y = alt.Y(f"{value}:Q", title=unit, scale=alt.Scale(zero=True), axis=axis)
    base = alt.Chart(frame).encode(x=x, y=y, tooltip=[
        alt.Tooltip("label:N", title="시각 (KST)"),
        alt.Tooltip(f"{value}:Q", title=unit, format=",.0f"),
    ])
    chart = (base.mark_line(color=AMBER, strokeWidth=2.5)
             + base.mark_point(color=AMBER, size=55, filled=True)).properties(height=172)
    st.altair_chart(_axis_config(chart), width="stretch", theme=None)


def bar_chart(data: list[dict[str, Any]], empty: str, title: str = "항목") -> None:
    if not data or not any(row["count"] for row in data):
        empty_chart(empty)
        return
    frame = pd.DataFrame(data)
    chart = (alt.Chart(frame).mark_bar(color=DARK, cornerRadiusEnd=5, height=17).encode(
        y=alt.Y("kind:N", title=None, sort=None, axis=alt.Axis(labelLimit=140, labelPadding=8)),
        x=alt.X("count:Q", title="건", scale=alt.Scale(zero=True),
                axis=alt.Axis(grid=True, tickMinStep=1, format="d")),
        tooltip=[alt.Tooltip("kind:N", title=title), alt.Tooltip("count:Q", title="건수", format="d")],
    ).properties(height=150, padding={"left": 36, "right": 8, "top": 4, "bottom": 4}))
    st.altair_chart(_axis_config(chart), width="stretch", theme=None)


def donut_chart(data: list[dict[str, Any]], domain: list[str], empty: str, title: str) -> None:
    if not data:
        empty_chart(empty)
        return
    frame = pd.DataFrame(data)
    chart = (alt.Chart(frame).mark_arc(innerRadius=56, outerRadius=88).encode(
        theta=alt.Theta("count:Q", stack=True),
        color=alt.Color("kind:N", title=title,
                        scale=alt.Scale(domain=domain, range=["#2D333A", "#D5A11B", "#98A6B1", "#607382"]),
                        legend=alt.Legend(orient="right", labelLimit=140)),
        tooltip=[alt.Tooltip("kind:N", title=title), alt.Tooltip("count:Q", title="건수", format="d")],
    ).properties(height=190))
    st.altair_chart(chart.configure_view(stroke=None).configure_legend(
        labelColor=MUTED, titleColor=MUTED, labelFontSize=13, titleFontSize=13), width="stretch", theme=None)


def provider_rows(states: list[tuple[str, str]]) -> None:
    rows = []
    for name, value in states:
        # A key or an HTTP response does not prove upstream availability.
        tone = "bad" if any(word in value for word in ("실패", "미설정", "중단")) else "muted"
        rows.append('<div class="cp-provider-row"><span>' + label(name)
                    + '</span><span class="cp-provider-status ' + tone + '"><i></i>' + label(value) + '</span></div>')
    st.markdown('<div class="cp-provider-list">' + "".join(rows) + '</div>', unsafe_allow_html=True)


def request_rows(observed: list[dict[str, Any]]) -> None:
    if not observed:
        empty_chart("현재 세션의 요청 기록이 없습니다")
        return
    rows = []
    for item in reversed(observed[-5:]):
        elapsed = "—" if item["elapsed_ms"] is None else f'{item["elapsed_ms"]:,.0f} ms'
        tone = ("bad" if item["state"] in ("실패", "차단") else "warn" if item["state"] == "부분 응답" else "neutral")
        rows.append('<div class="cp-event-row"><span>' + label(display_time(item["time"])) + '</span><b>'
                    + label(item["kind"]) + '</b><span class="cp-event-state ' + tone + '">'
                    + label(item["state"]) + '</span><span>' + label(elapsed) + '</span></div>')
    st.markdown('<div class="cp-event-list">' + "".join(rows) + '</div>', unsafe_allow_html=True)


def trace_table(observed: list[dict[str, Any]]) -> None:
    if not observed:
        st.caption("현재 세션의 요청 기록이 없습니다.")
        return
    records = [{
        "시각 (KST)": display_time(item["time"], full=True),
        "요청 ID": item.get("request_id") or "—",
        "요청": item["kind"],
        "Planner 판정": PLAN_STATUS_LABELS.get(item["plan_status"], "—") if item["plan_status"] else "—",
        "Critic 판정": item["critic_decision"] or "—",
        "결과": item["state"],
        "오류 구분": item["error_class"] or "—",
        "소요 (ms)": item["elapsed_ms"],
    } for item in reversed(observed[-20:])]
    st.dataframe(pd.DataFrame(records), hide_index=True, width="stretch", height=260)


def action_list(actions: list[dict[str, str]]) -> None:
    if not actions:
        empty_chart("조치가 필요한 항목이 없습니다")
        return
    rows = []
    for item in actions:
        rows.append('<div class="cp-action-row"><i class="' + label(item["level"]) + '"></i><div><b>'
                    + label(item["title"]) + '</b><small>' + label(item["detail"]) + '</small></div>'
                    '<span class="cp-action-ref">' + label(item["ref"]) + '</span></div>')
    st.markdown('<div class="cp-action-list">' + "".join(rows) + '</div>', unsafe_allow_html=True)


def stage_flow(stages: list[tuple[str, str, str]]) -> None:
    """Ordered processing stages: (name, value, basis)."""
    parts = []
    for index, (name, value, basis) in enumerate(stages, start=1):
        parts.append('<div class="cp-stage"><span class="cp-stage-index">' + f"{index:02d}"
                     + '</span><b>' + label(name) + '</b><strong>' + label(value) + '</strong><small>'
                     + label(basis) + '</small></div>')
    st.markdown('<div class="cp-stage-flow" style="--stages:' + str(len(stages)) + '">'
                + "".join(parts) + '</div>', unsafe_allow_html=True)


NOWRAP_COLUMNS = {"ID", "영역", "출처", "계층", "판정", "상태", "범주", "장애 유형"}


def policy_table(rows: list[dict[str, str]], height: int | None = None) -> None:
    head = "".join('<th>' + label(key) + '</th>' for key in rows[0]) if rows else ""
    body = []
    for row in rows:
        cells = []
        for key, value in row.items():
            css = ' class="nowrap"' if key in NOWRAP_COLUMNS else ""
            cells.append('<td' + css + '>' + (status_tag(value) if key in ("판정", "상태") else label(value)) + '</td>')
        body.append('<tr>' + "".join(cells) + '</tr>')
    style = f' style="max-height:{height}px"' if height else ""
    st.markdown('<div class="cp-table-wrap"' + style + '><table class="cp-table"><thead><tr>' + head
                + '</tr></thead><tbody>' + "".join(body) + '</tbody></table></div>', unsafe_allow_html=True)


def app_topbar(title: str) -> None:
    st.markdown('<div class="cp-dashboard-title"><span></span><h2>' + label(title)
                + '</h2></div><div class="cp-dashboard-subtitle">' + label(MENU_SCOPES.get(title, ""))
                + '</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- GitHub (public API, cached)

@st.cache_data(ttl=120, show_spinner=False)
def github_runs() -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = requests.get(REPO_API + "/actions/runs", params={"per_page": 20},
                                headers={"Accept": "application/vnd.github+json"}, timeout=6)
        if response.status_code != 200:
            return [], f"GitHub 응답 {response.status_code} · 저장소 공개 여부와 접근 권한을 확인해 주세요."
        return response.json().get("workflow_runs", []), None
    except (requests.RequestException, ValueError):
        return [], "GitHub 실행 이력을 불러오지 못했습니다."


@st.cache_data(ttl=120, show_spinner=False)
def github_jobs(run_id: int) -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = requests.get(f"{REPO_API}/actions/runs/{run_id}/jobs", params={"per_page": 100},
                                headers={"Accept": "application/vnd.github+json"}, timeout=6)
        if response.status_code != 200:
            return [], f"작업 조회 실패 · HTTP {response.status_code}"
        return response.json().get("jobs", []), None
    except (requests.RequestException, ValueError):
        return [], "작업 이력을 불러오지 못했습니다."


@st.cache_data(ttl=120, show_spinner=False)
def latest_main_run() -> tuple[dict[str, Any] | None, str | None]:
    try:
        response = requests.get(REPO_API + "/actions/workflows/ci.yml/runs",
                                params={"branch": "main", "event": "push", "per_page": 1},
                                headers={"Accept": "application/vnd.github+json"}, timeout=6)
        if response.status_code != 200:
            return None, f"main 실행 조회 실패 · HTTP {response.status_code}"
        runs = response.json().get("workflow_runs", [])
        return (runs[0] if runs else None), None
    except (requests.RequestException, ValueError):
        return None, "main 실행 이력을 불러오지 못했습니다."


def job_status(job: dict[str, Any] | None) -> str:
    if not job:
        return "확인 필요"
    if job.get("status") != "completed":
        return "진행 중"
    return {"success": "성공", "failure": "실패", "cancelled": "취소",
            "skipped": "건너뜀", "timed_out": "시간 초과"}.get(job.get("conclusion"), "확인 필요")


def run_state(run: dict[str, Any] | None) -> str:
    if not run:
        return "확인 필요"
    if run.get("status") in ("in_progress", "queued"):
        return "진행 중"
    return {"success": "성공", "failure": "실패", "cancelled": "취소"}.get(run.get("conclusion"), "확인 필요")


TEST_JOBS = ("Backend unit tests", "Frontend syntax check", "Existing Auto Healing policy tests")
BUILD_JOB = "Validate Compose and build images"
PUBLISH_JOB = "Publish both images to GHCR (main only)"


def pipeline_status(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Gate states from the latest CI run and the latest main push run."""
    latest_ci = next((run for run in runs if run.get("name") == "ChargePin CI"), None)
    result: dict[str, Any] = {"run": latest_ci, "tests": "확인 필요", "tests_detail": "최근 CI 실행 없음",
                              "build": "확인 필요", "publish": "확인 필요", "publish_detail": "main 게시 실행 없음",
                              "jobs": {}}
    if latest_ci and isinstance(latest_ci.get("id"), int):
        jobs, error = github_jobs(latest_ci["id"])
        by_name = {job.get("name"): job for job in jobs}
        result["jobs"] = {name: job_status(by_name.get(name)) for name in (*TEST_JOBS, BUILD_JOB, PUBLISH_JOB)}
        states = [result["jobs"][name] for name in TEST_JOBS]
        if error:
            result["tests"], result["tests_detail"] = "조회 실패", error
        elif not all(name in by_name for name in TEST_JOBS):
            result["tests_detail"] = "테스트 작업 정보가 불완전합니다"
        else:
            result["tests"] = ("실패" if any(state in ("실패", "시간 초과") for state in states)
                               else "진행 중" if "진행 중" in states
                               else "성공" if all(state == "성공" for state in states) else "확인 필요")
            result["tests_detail"] = f"CI #{latest_ci.get('run_number', '—')} · {latest_ci.get('head_branch', '—')}"
        result["build"] = result["jobs"].get(BUILD_JOB, "확인 필요")
    main_run, error = latest_main_run()
    if error:
        result["publish_detail"] = error
    elif main_run and isinstance(main_run.get("id"), int):
        jobs, error = github_jobs(main_run["id"])
        job = next((item for item in jobs if item.get("name") == PUBLISH_JOB), None)
        result["publish"] = "조회 실패" if error else job_status(job)
        result["publish_detail"] = error or f"main CI #{main_run.get('run_number', '—')}"
    return result


# ---------------------------------------------------------------- views

def operations_action_panel(api: Any, server: dict[str, Any] | None) -> None:
    """Run only administrator-authorized, auditable operation endpoints."""
    with st.container(border=True, key="overview_operation_actions"):
        section_title("운영 작업", "실패 요청 재처리 · 제공자 캐시 갱신")
        notice = st.session_state.pop("operation_notice", None)
        if isinstance(notice, str):
            st.success(notice)
        if server is None:
            st.info("운영 API 연결을 확인하는 중입니다.")
            return
        token = st.session_state.get("access_token")
        if not isinstance(token, str) or not token:
            st.warning("운영 세션을 다시 확인해 주세요.")
            return

        candidates = []
        for event in server.get("recent_events", []):
            if not isinstance(event, dict) or event.get("event_type") != "search" or event.get("status") != "degraded":
                continue
            request_id = event.get("request_id")
            if isinstance(request_id, str) and 0 < len(request_id) <= 80 and request_id.isascii():
                candidates.append(request_id)
        candidates = list(dict.fromkeys(candidates))
        left, right = st.columns(2, gap="medium")
        with left:
            if candidates:
                request_id = st.selectbox("재처리할 불완전 검색 요청", candidates, key="operation_retry_request")
                if st.button("선택 요청 재처리", icon=":material/replay:", use_container_width=True,
                             key="operation_retry"):
                    try:
                        result = api.retry_request(request_id, token)
                    except ApiError as error:
                        st.error(error.message)
                    else:
                        st.session_state.operation_notice = (
                            f"요청을 재처리했습니다. 결과 상태: {result.get('status', '확인 필요')}"
                        )
                        st.rerun()
            else:
                st.caption("현재 세션에 재처리 가능한 불완전 검색 요청이 없습니다.")
        with right:
            st.caption("카카오 장소 후보와 환경공단 충전기 캐시를 비웁니다. 다음 검색에서 새로 조회합니다.")
            if st.button("캐시 갱신", icon=":material/refresh:", use_container_width=True, key="operation_cache_refresh"):
                try:
                    api.refresh_cache(token)
                except ApiError as error:
                    st.error(error.message)
                else:
                    st.session_state.operation_notice = "제공자 캐시를 갱신했습니다."
                    st.rerun()


def overview_view(data: dict[str, Any], guard: dict[str, Any], health: str,
                  providers: list[tuple[str, str]], items: list[dict[str, Any]], pipeline: dict[str, Any],
                  api: Any, server: dict[str, Any] | None) -> None:
    score = compliance_score(items)
    rate = "—" if data["server_error_rate"] is None else f'{data["server_error_rate"]:.1f}%'
    metric_row("overview_metrics", [
        ("서비스 상태", health, "/healthz · 실시간", "good" if health == "정상" else "bad" if health == "중단" else "warn", "pulse"),
        ("서버 측 오류율", rate, f'5xx · 연결 실패 {data["server_error_count"]:,}건 / 요청 {len(data["observed"]):,}건',
         "bad" if data["server_error_count"] else "neutral", "alert"),
        ("가드레일 판정", f'{guard["input_checked"] + guard["output_checked"]:,}건',
         f'입력 차단 {guard["input_blocked"]:,} · 안전 응답 {guard["output_safe"]:,} · 현재 세션', "neutral", "shield"),
        ("증빙 확보", f'{score["met"]} / {score["total"]}', "컴플라이언스 자가 점검 · 충족 항목", "neutral", "check"),
    ])
    with st.container(key="overview_charts"):
        left, right = st.columns([1.25, 1], gap="medium")
        with left:
            with st.container(border=True, key="overview_request_trend"):
                section_title("검색 요청 추이", "현재 세션 · 분 단위")
                line_chart(data["minute_counts"], "count", "건", "선택 기간에 기록된 검색 요청이 없습니다")
        with right:
            with st.container(border=True, key="overview_actions"):
                section_title("조치 필요 항목", "실시간 이상 → 미착수 → 부분 순")
                action_list(action_items(items, data, health))
    with st.container(key="overview_details"):
        request_col, provider_col, deploy_col = st.columns([1.1, 1, 1], gap="medium")
        with request_col:
            with st.container(border=True, key="overview_recent_requests"):
                section_title("최근 요청", "최대 5건 · KST")
                request_rows(data["observed"])
        with provider_col:
            with st.container(border=True, key="overview_providers"):
                section_title("외부 연결", "설정 여부 · 최근 관측")
                provider_rows(providers)
        with deploy_col:
            with st.container(border=True, key="overview_pipeline"):
                section_title("배포 파이프라인", "GitHub 실시간 · EC2 수동")
                run = pipeline["run"]
                provider_rows([
                    ("테스트 게이트", pipeline["tests"]),
                    ("이미지 게시", pipeline["publish"]),
                    ("최근 실행 시각", display_time(event_time(run.get("created_at")), full=True) if run else "확인 필요"),
                    ("EC2 배포", "수동 · 관리표 기록"),
                ])
                st.link_button("GitHub Actions 실행 보기", (run or {}).get("html_url") or ACTIONS_URL, width="stretch")
    operations_action_panel(api, server)


def agent_view(data: dict[str, Any], guard: dict[str, Any]) -> None:
    counts = {row["kind"]: row["count"] for row in data["kind_counts"]}
    average = "—" if data["average_ms"] is None else f'{data["average_ms"]:,} ms'
    metric_row("agent_kpis", [
        ("챗 해석", f'{counts.get("챗 해석", 0):,}건', "Planner · 현재 세션", "neutral", "chat"),
        ("충전소 검색", f'{data["search_count"]:,}건', "Executor · 직접 검색 + 챗 검색", "neutral", "search"),
        ("Critic 판정", f'{guard["output_checked"]:,}건', f'PASS {guard["output_pass"]:,} · SAFE_UNAVAILABLE {guard["output_safe"]:,}',
         "warn" if guard["output_safe"] else "neutral", "judge"),
        ("검색 응답 시간", average, "평균 · 프론트 왕복 기준", "neutral", "clock"),
    ])
    with st.container(border=True, key="agent_flow"):
        section_title("에이전트 처리 단계", "현재 세션 · 단계별 관측 건수")
        stage_flow([
            ("요청 접수", f'{len(data["observed"]):,}건', "프론트 관측"),
            ("Planner 해석", f'{guard["input_checked"]:,}건', "자연어 → 검색 조건"),
            ("입력 가드레일", f'통과 {guard["input_passed"]:,} · 차단 {guard["input_blocked"]:,}', "Planner 이전 판정"),
            ("Executor 조회", f'{data["search_count"]:,}건', "카카오 · 환경공단"),
            ("Critic 검증", f'{guard["output_checked"]:,}건', "PASS · SAFE_UNAVAILABLE"),
            ("응답", f'{sum(item["state"] in ("응답", "부분 응답") for item in data["searches"]):,}건', "검색 결과 반환"),
        ])
        st.caption("Memory Keeper의 단계별 Handoff 기록은 서버 집계 연결 후 같은 요청 ID로 표시합니다.")
    with st.container(key="agent_charts"):
        left, right = st.columns([1.2, 1], gap="medium")
        with left:
            with st.container(border=True, key="agent_plan"):
                section_title("Planner 판정 분포", "현재 세션 · 건")
                bar_chart(data["plan_counts"], "챗 해석 요청이 기록되면 표시합니다", "판정")
        with right:
            with st.container(border=True, key="agent_availability"):
                section_title("충전 상태 판정 구성", "검색 결과 기준 · 비중")
                donut_chart(data["availability_counts"], list(AVAILABILITY_LABELS.values()),
                            "검색 결과가 기록되면 표시합니다", "충전 상태")
    with st.container(border=True, key="agent_trace"):
        section_title("요청 추적", "현재 세션 · 최근 20건 · 요청 ID 기준")
        trace_table(data["observed"])


GUARDRAIL_POLICIES = [
    {"범주": "PROMPT_OVERRIDE", "차단 대상": "시스템 · 개발자 지침 무시, 숨겨진 프롬프트 공개 요청", "판정": "구현"},
    {"범주": "SECRET_REQUEST", "차단 대상": "환경변수 · API 키 · 토큰 · 비밀번호 요청", "판정": "구현"},
    {"범주": "OTHER_USER_DATA", "차단 대상": "다른 사용자의 대화 · 기록 · 정보 요청", "판정": "구현"},
    {"범주": "PRIVILEGE_CHANGE", "차단 대상": "권한 · 역할 변경, 관리자 승급 요청", "판정": "구현"},
]


def guardrail_view(data: dict[str, Any], guard: dict[str, Any], server: dict[str, Any] | None,
                   items: list[dict[str, Any]]) -> None:
    status = {item.get("id"): item["status"] for item in items}
    server_metrics = (server or {}).get("metrics", {}) if isinstance(server, dict) else {}
    metric_row("guardrail_kpis", [
        ("입력 검사", f'{guard["input_checked"]:,}건', f'차단 {guard["input_blocked"]:,} · 통과 {guard["input_passed"]:,}',
         "warn" if guard["input_blocked"] else "neutral", "shield"),
        ("출력 검증", f'{guard["output_checked"]:,}건', f'안전 응답 {guard["output_safe"]:,} · PASS {guard["output_pass"]:,}',
         "warn" if guard["output_safe"] else "neutral", "judge"),
        ("접근 거부", f'{guard["access_denied"]:,}건', "401 · 403 응답 · 현재 세션", "bad" if guard["access_denied"] else "neutral", "lock"),
        ("품질 경고", f'{guard["finding_count"]:,}건', "Critic 지적 사항 수 · 내용 미수집", "neutral", "flag"),
    ])
    with st.container(border=True, key="guardrail_layers"):
        section_title("계층별 정책 판정", "통과도 기록 · 현재 세션 / 서버 집계")
        server_block = server_metrics.get("guardrail_block_count")
        policy_table([
            {"계층": "입력", "통제": "InputGuardrail 4개 범주, Planner 이전 실행",
             "현재 세션": f'차단 {guard["input_blocked"]} · 통과 {guard["input_passed"]}',
             "서버 집계": f"차단 {server_block}" if isinstance(server_block, int) else "연결 대기", "판정": status.get("G-1", "구현")},
            {"계층": "행동", "통제": "Planner 도구 없음 · Executor만 카카오·환경공단 호출",
             "현재 세션": "코드 기준 · 이벤트 미수집", "서버 집계": "연결 대기", "판정": status.get("A-2", "구현")},
            {"계층": "출력", "통제": "Critic PASS / SAFE_UNAVAILABLE, 확인 불가 상태 단정 금지",
             "현재 세션": f'PASS {guard["output_pass"]} · 안전 응답 {guard["output_safe"]}',
             "서버 집계": (f'완료 {server_metrics["completed_count"]} · 부분 {server_metrics["degraded_count"]}'
                       if isinstance(server_metrics.get("completed_count"), int) and isinstance(server_metrics.get("degraded_count"), int) else "연결 대기"),
             "판정": status.get("G-2", "구현")},
            {"계층": "접근", "통제": "운영 API 관리자 전용(403), 대시보드 역할 제한",
             "현재 세션": f'거부 {guard["access_denied"]}', "서버 집계": "연결 대기", "판정": status.get("G-3", "구현")},
        ])
    with st.container(key="guardrail_details"):
        left, right = st.columns([1, 1.2], gap="medium")
        with left:
            with st.container(border=True, key="guardrail_errors"):
                section_title("오류 분리", "요청 측 · 서버 측 · 연결 · 현재 세션")
                bar_chart(data["error_counts"], "현재 세션에 오류 응답이 없습니다", "구분")
                st.caption("요청 측 4xx는 입력·권한 문제, 서버 측 5xx와 연결 실패는 운영 조치 대상입니다.")
        with right:
            with st.container(border=True, key="guardrail_policies"):
                section_title("입력 차단 정책", "Policy as Code · Backend/app/agents.py")
                categories = server_metrics.get("guardrail_category_counts")
                categories = categories if isinstance(categories, dict) else None
                rows = []
                for row in GUARDRAIL_POLICIES:
                    count = categories.get(row["범주"]) if categories else None
                    rows.append({**row, "서버 차단": str(count) if isinstance(count, int) and not isinstance(count, bool) and count >= 0
                                 else "연결 대기"})
                policy_table(rows)
                st.caption("범주별 차단 건수는 서버 감사 이벤트 집계(guardrail_category_counts)입니다. 차단된 원문은 저장하지 않습니다.")


def reliability_view(data: dict[str, Any], guard: dict[str, Any], health: str,
                     providers: list[tuple[str, str]], reference: dict[str, Any],
                     healing: dict[str, Any] | None, server: dict[str, Any] | None) -> None:
    checks = {item.get("title"): item for item in reference.get("checks", [])}
    trial = checks.get("자동복구 실증", {})
    drills = checks.get("필수 장애시험", {})
    stats = healing_stats(healing)
    average = "—" if data["average_ms"] is None else f'{data["average_ms"]:,} ms'
    rate = "—" if data["server_error_rate"] is None else f'{data["server_error_rate"]:.1f}%'
    if stats["rate"] is not None:
        heal_card = ("자동 복구율", f'{stats["rate"]:.1f}%',
                     f'복구 {stats["recovered"]} / 재시작 {stats["attempts"]}'
                     + (f' · 평균 {stats["average_seconds"]}초' if stats["average_seconds"] is not None else "")
                     + " · 서버 이벤트", "good" if stats["rate"] == 100 else "warn", "heal")
    else:
        heal_card = ("자동 복구 실증", str(trial.get("status", "확인 필요")),
                     str(trial.get("detail", "")) + " · 관리표 기록", "neutral", "heal")
    metric_row("reliability_kpis", [
        ("헬스 체크", health, "ok · degraded · down 기준", "good" if health == "정상" else "bad" if health == "중단" else "warn", "pulse"),
        ("검색 응답 시간", average, "평균 · 프론트 왕복 · 현재 세션", "neutral", "clock"),
        ("서버 측 오류율", rate, "5xx · 연결 실패 / 전체 요청", "bad" if data["server_error_count"] else "neutral", "alert"),
        heal_card,
    ])

    # Auto Healing: policy (server-reported, else ops/autoheal.py defaults) and recorded events.
    with st.container(key="healing_details"):
        left, right = st.columns([1, 1.3], gap="medium")
        with left:
            with st.container(border=True, key="healing_policy"):
                policy = (healing or {}).get("policy") or {}
                from_server = any(value not in (None, [], "") for value in policy.values())
                basis = "서버 보고" if from_server else "코드 기준 · ops/autoheal.py"
                section_title("Auto Healing 정책", basis)
                source = policy if from_server else CODE_HEALING_POLICY
                def show(value: Any, unit: str = "") -> str:
                    return "확인 필요" if value in (None, "") else f"{value}{unit}"
                provider_rows([
                    ("동작 모드", show(source.get("mode"))),
                    ("재시작 조건", "unhealthy 연속 " + show(source.get("consecutive_unhealthy"), "회")),
                    ("재시작 간격", show(source.get("cooldown_seconds"), "초") + " 쿨다운"),
                    ("재시작 상한", show(source.get("max_restarts"), "회") + " / " + show(source.get("window_seconds"), "초")),
                    ("복구 대기 한도", show(source.get("recovery_timeout_seconds"), "초")),
                    ("대상", ", ".join(source.get("scope") or []) or "확인 필요"),
                ])
                st.caption("멈춘 컨테이너는 재시작하지 않고, 상한을 넘으면 사람이 확인합니다.")
        with right:
            with st.container(border=True, key="healing_events"):
                section_title("힐링 이벤트", "재시작 시도 · 복구 · 시간 초과")
                events = (healing or {}).get("events") or []
                if healing is None:
                    empty_chart("서버 연결 대기 · GET /api/v1/ops/healing")
                elif not events:
                    empty_chart("기록된 힐링 이벤트가 없습니다")
                else:
                    labels = {"restart_attempt": "재시작 시도", "recovered": "복구", "recovery_timeout": "복구 시간 초과",
                              "restart_failed": "재시작 실패", "state_changed": "상태 변경", "recovery_interrupted": "복구 중단"}
                    rows = [{"시각 (KST)": display_time(item["time"], full=True), "이벤트": labels[item["event"]],
                             "컨테이너": item["container"] or "—",
                             "복구 시간": f'{item["duration_seconds"]}초' if item["duration_seconds"] is not None else "—"}
                            for item in reversed(events[-20:]) if item["event"] != "state_changed"]
                    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=min(40 + 35 * len(rows), 280))

    retry_count = ((server or {}).get("metrics") or {}).get("retry_count") if isinstance(server, dict) else None
    with st.container(border=True, key="healing_layers"):
        section_title("힐링 계층", "가장 가벼운 조치부터, 넘치면 다음 계층으로")
        policy_table([
            {"계층": "L1 재시작", "동작": "Docker Compose Health Check · Watchdog 컨테이너 재시작",
             "트리거": "헬스 체크 연속 실패",
             "현재 근거": (f'재시작 {stats["attempts"]} · 복구 {stats["recovered"]} (서버 이벤트)' if healing
                       else f'{trial.get("status", "확인 필요")} · {trial.get("detail", "")}'),
             "판정": "부분"},
            {"계층": "L2 재처리", "동작": "503 재시도 안내 · 관리자 재처리(최대 2회)",
             "트리거": "외부 API 지연 · 호출 제한",
             "현재 근거": f"서버 재처리 {retry_count}건" if isinstance(retry_count, int) else "서버 집계 연결 대기",
             "판정": "구현"},
            {"계층": "L3 안전 응답", "동작": "Critic SAFE_UNAVAILABLE · LLM 실패 시 검색 중단",
             "트리거": "확인 불가 데이터 · LLM 호출 실패",
             "현재 근거": f'세션 안전 응답 {guard["output_safe"]}건', "판정": "구현"},
            {"계층": "L4 사람", "동작": "실패 알림 → 담당자 에스컬레이션",
             "트리거": "재시작 상한 초과 · 복구 시간 초과",
             "현재 근거": "알림 수신 증빙 없음", "판정": "미착수"},
        ])
        st.caption(f'필수 장애시험: {drills.get("status", "확인 필요")} · {drills.get("detail", "")} (관리표 기록)')

    availability = {row["kind"]: row["count"] for row in data["availability_counts"]}
    with st.container(key="reliability_charts"):
        left, right = st.columns([1.2, 1], gap="medium")
        with left:
            with st.container(border=True, key="reliability_latency"):
                section_title("검색 응답 시간", "ms · 프론트 왕복 · 현재 세션")
                points = [{"time": item["time"].isoformat(), "elapsed_ms": item["elapsed_ms"]}
                          for item in data["searches"] if item["elapsed_ms"] is not None]
                line_chart(points, "elapsed_ms", "ms", "검색 응답 시간이 기록되면 표시합니다")
        with right:
            with st.container(border=True, key="reliability_providers"):
                section_title("의존성 상태", "백엔드 · 외부 API · 캐시")
                provider_rows([("백엔드 /healthz", health), *providers])
    with st.expander("장애 유형별 대응", expanded=False):
        policy_table([
            {"장애 유형": "프로세스 중단", "감지 신호": "컨테이너 헬스체크 실패", "대응": "L1 재시작", "판정": "부분"},
            {"장애 유형": "일시 오류", "감지 신호": "5xx · 429 · 응답 지연", "대응": "L2 재처리",
             "현재 근거": f'세션 서버 측 오류 {data["server_error_count"]}건', "판정": "구현"},
            {"장애 유형": "기능 불능", "감지 신호": "LLM 호출 실패 · 제공처 인증 만료(401)", "대응": "L3 안전 응답",
             "현재 근거": f'세션 안전 응답 {guard["output_safe"]}건', "판정": "구현"},
            {"장애 유형": "데이터 지연", "감지 신호": "충전 상태 정보 지연", "대응": "지연 표시, 단정하지 않음",
             "현재 근거": f'세션 정보 지연 {availability.get("정보 지연", 0)}건', "판정": "구현"},
        ])


def compose_platform_panel(platform: dict[str, Any] | None) -> None:
    with st.container(border=True, key="pipeline_compose_platform"):
        if platform is None:
            section_title("Docker Compose 서비스 상태", "서버 연결 대기 · GET /api/v1/ops/platform")
            policy_table([{"종류": kind, "이름": name, "역할": role, "상태": "연결 대기"}
                          for kind, name, role in EXPECTED_RESOURCES])
            st.caption("백엔드가 Compose 서비스 상태를 보내면 준비 상태, 이미지 태그, Health Check와 운영 설정 수가 표시됩니다. 비밀값은 표시하지 않습니다.")
            return
        when = display_time(platform["observed_at"].astimezone(KST), full=True) if platform["observed_at"] else "시각 확인 필요"
        section_title("Docker Compose 서비스 상태",
                      f'{platform["namespace"] or "Compose 프로젝트 확인 필요"} · {when}')
        def num(value: Any) -> str:
            return "—" if value is None else str(value)
        rows = []
        for item in platform["workloads"]:
            ready = item["desired"] is not None and item["ready"] is not None and item["ready"] >= item["desired"] > 0
            tag = (item["image"] or "—").rsplit(":", 1)[-1] if item["image"] else "—"
            rows.append({"종류": item["kind"], "이름": item["name"], "준비 / 목표": f'{num(item["ready"])} / {num(item["desired"])}',
                         "재시작": num(item["restarts"]), "이미지 태그": tag,
                         "프로브": " · ".join(x for x in (item["liveness"], item["readiness"]) if x) or "—",
                         "상태": "성공" if ready else "부분"})
        if rows:
            policy_table(rows)
        else:
            empty_chart("보고된 워크로드가 없습니다")
        extra = [{"종류": "Service", "이름": item["name"], "유형": item["type"] or "—", "포트": num(item["port"]),
                  "엔드포인트": num(item["endpoints"])} for item in platform["services"]]
        extra += [{"종류": item["kind"], "이름": item["name"], "유형": "키 " + num(item["keys"]) + "개", "포트": "—",
                   "엔드포인트": "—"} for item in platform["config"]]
        if extra:
            policy_table(extra)


def pipeline_view(reference: dict[str, Any], pipeline: dict[str, Any], runs: list[dict[str, Any]],
                  runs_error: str | None, platform: dict[str, Any] | None = None) -> None:
    reference_date = str(reference.get("source_date", "확인 필요"))
    run = pipeline["run"]
    metric_row("pipeline_kpis", [
        ("최근 실행", run_state(run), (run or {}).get("head_branch") or "GitHub Actions", STATUS_TONES.get(run_state(run), "neutral"), "branch"),
        ("테스트 게이트", pipeline["tests"], pipeline["tests_detail"], STATUS_TONES.get(pipeline["tests"], "neutral"), "check"),
        ("이미지 게시", pipeline["publish"], pipeline["publish_detail"], STATUS_TONES.get(pipeline["publish"], "neutral"), "package"),
        ("EC2 배포", "수동", "관리표 기록 · " + reference_date, "neutral", "server"),
    ])
    with st.container(border=True, key="pipeline_gates"):
        section_title("단계별 정책 게이트", "선행 단계 실패 시 후속 단계 생략 · ci.yml needs")
        stage_flow([
            ("테스트 게이트", pipeline["tests"], "백엔드 단위 · 프론트 문법 · Auto Healing"),
            ("빌드 게이트", pipeline["build"], "Compose 검증 · 이미지 빌드"),
            ("이미지 게시", pipeline["publish"], "main push만 GHCR"),
            ("EC2 배포", "수동", "관리표 기록 · 자동 CD 보류"),
            ("운영 확인", "수동", "헬스 확인 · 자동화 예정"),
        ])
        st.caption("Plan · Code는 저장소 브랜치, Build · Test · Release는 GitHub Actions 자동, Deploy · Operate는 현재 수동입니다.")
    compose_platform_panel(platform)
    with st.container(key="pipeline_details"):
        left, right = st.columns([1.2, 1], gap="medium")
        with left:
            with st.container(border=True, key="pipeline_runs"):
                section_title("최근 실행", "워크플로 · 브랜치 · 결과 · 시작 시각")
                if runs_error:
                    st.info(runs_error)
                elif not runs:
                    empty_chart("실행 이력이 없습니다")
                else:
                    records = [{"워크플로": item.get("name", "—"), "브랜치": item.get("head_branch", "—"),
                                "결과": run_state(item),
                                "시작 시각": display_time(event_time(item.get("created_at")), full=True)}
                               for item in runs[:8]]
                    st.dataframe(pd.DataFrame(records), hide_index=True, width="stretch")
                    st.link_button("GitHub Actions에서 보기", ACTIONS_URL)
        with right:
            with st.container(border=True, key="pipeline_checks"):
                section_title("실패 처리 · 증빙", "관리표 기록 · " + reference_date)
                rows = []
                for check in reference.get("checks", []):
                    rows.append('<div class="cp-provider-row"><span>' + label(check.get("title", ""))
                                + '</span><span class="cp-check-tag">' + label(check.get("status", "확인 필요"))
                                + '</span></div>')
                st.markdown('<div class="cp-provider-list">' + "".join(rows) + '</div>', unsafe_allow_html=True)
                st.link_button("배포 · 운영 관리표", SHEET_URL, width="stretch")


def compliance_view(reference: dict[str, Any], items: list[dict[str, Any]]) -> None:
    score = compliance_score(items)
    counts = {row["kind"]: row["count"] for row in score["counts"]}
    metric_row("compliance_kpis", [
        ("충족", f'{counts["충족"]}건', "구현 + 실행 증빙", "good", "check"),
        ("구현", f'{counts["구현"]}건', "코드 · 문서 · 실행 증빙 대기", "neutral", "shield"),
        ("부분", f'{counts["부분"]}건', "일부 구현 · 일부 증빙", "warn", "alert"),
        ("미착수", f'{counts["미착수"]}건', "구현 또는 증빙 없음", "bad", "flag"),
    ])
    areas = {area["key"]: area["label"] for area in reference.get("areas", [])}
    choices = ["전체", *[f"{key} {value}" for key, value in areas.items()]]
    with st.container(border=True, key="compliance_report"):
        head, tools = st.columns([2, 1], gap="small", vertical_alignment="center")
        with head:
            section_title("컴플라이언스 리포트", f'기준일 {reference.get("source_date", "확인 필요")} · 증빙 확보 {score["met"]} / {score["total"]}')
        selected = st.radio("영역", choices, horizontal=True, label_visibility="collapsed", key="compliance_area")
        key = selected.split(" ", 1)[0]
        visible = items if selected == "전체" else [item for item in items if item.get("area") == key]
        rows = compliance_rows(visible)
        for row in rows:
            row["영역"] = areas.get(row["영역"], row["영역"])
        policy_table(rows)
        st.caption(str(reference.get("basis", "")))
        with tools:
            csv = pd.DataFrame(compliance_rows(items)).to_csv(index=False).encode("utf-8-sig")
            allowed = can_export_report(st.session_state.get("role"))
            st.download_button("리포트 내보내기 (CSV)", csv, file_name="chargepin_compliance_report.csv",
                               mime="text/csv", icon=":material/download:", disabled=not allowed,
                               help=None if allowed else "상급 관리자만 내보낼 수 있습니다.", key="compliance_export")
    with st.expander("판정 기준", expanded=False):
        legend = reference.get("status_legend", {})
        st.markdown("".join('<div class="cp-provider-row"><span>' + status_tag(key) + '</span><span>' + label(value)
                            + '</span></div>' for key, value in legend.items()), unsafe_allow_html=True)
        st.caption("실시간 신호(헬스 체크, 세션 판정, CI 결과)는 '구현' 항목만 '충족'으로 올립니다. 부분 · 미착수 항목은 바꾸지 않습니다.")


# ---------------------------------------------------------------- dialogs and shell

def render_operations_dashboard(api: Any, header: Callable[..., str | None],
                                providers: Callable[[], list[tuple[str, str]]],
                                reference_loader: Callable[[], dict[str, Any]],
                                server_summary_loader: Callable[[], dict[str, Any] | None] | None = None,
                                platform_loader: Callable[[], dict[str, Any] | None] | None = None,
                                healing_loader: Callable[[], dict[str, Any] | None] | None = None) -> None:
    """Optional server hooks (handoff/2026-11-08/BACKEND_HANDOFF.md):
    server_summary_loader → GET /api/v1/ops/summary, platform_loader → GET /api/v1/ops/platform,
    healing_loader → GET /api/v1/ops/healing. A hook that is missing or fails renders "연결 대기"."""
    def navigation() -> str | None:
        with st.container(key="header_menu", width="stretch"):
            return st.radio("운영 메뉴", MENUS, horizontal=True, label_visibility="collapsed",
                            key="dashboard_navigation")

    with st.container(key="dashboard_header"):
        menu = header(dashboard_view=True, navigation=navigation)
    try:
        health = health_label(api.health(), True)
    except ApiError:
        health = health_label(None, False)
    menu = menu if menu in MENUS else MENUS[0]
    with st.container(key="dashboard_page_heading"):
        title_col, toolbar_col = st.columns([1.3, 3], gap="small", vertical_alignment="center")
        with title_col:
            app_topbar(menu)
        with toolbar_col:
            with st.container(key="dashboard_toolbar", horizontal=True, horizontal_alignment="right",
                              vertical_alignment="center", gap="small"):
                with st.container(key="dashboard_period_control", horizontal=True, vertical_alignment="center",
                                  gap="small", width="content"):
                    st.markdown('<span class="cp-toolbar-label">조회 기간</span>', unsafe_allow_html=True, width="content")
                    period = st.radio("조회 기간", ["1시간", "24시간", "7일"], index=1, horizontal=True,
                                      label_visibility="collapsed", key="dashboard_period", width="content")
                now = datetime.now(KST).strftime("%Y.%m.%d %H:%M:%S")
                st.markdown('<div class="cp-dashboard-updated">최종 업데이트 <b>' + now + ' KST</b></div>',
                            unsafe_allow_html=True, width="content")
                if st.button("갱신", icon=":material/refresh:", key="dashboard_refresh"):
                    github_runs.clear()
                    github_jobs.clear()
                    latest_main_run.clear()
                    st.rerun()
    cutoff = datetime.now(KST) - timedelta(hours={"1시간": 1, "24시간": 24, "7일": 168}[period])
    events = [event for event in st.session_state.get("api_events", [])
              if (when := event_time(event.get("observed_at"))) is not None and when >= cutoff]
    data = summarize_events(events)
    guard = guardrail_summary(data)
    reference = reference_loader()
    def load(loader: Callable[[], Any] | None) -> Any:
        if loader is None:
            return None
        try:
            return loader()
        except (ApiError, requests.RequestException, ValueError):
            return None

    server = load(server_summary_loader) if menu in ("운영 개요", "가드레일", "안정성·힐링") else None
    platform = normalize_platform(load(platform_loader)) if menu in ("배포 파이프라인", "컴플라이언스", "운영 개요") else None
    healing = normalize_healing(load(healing_loader)) if menu in ("안정성·힐링", "컴플라이언스", "운영 개요") else None
    needs_pipeline = menu in ("운영 개요", "배포 파이프라인", "컴플라이언스")
    runs, runs_error = github_runs() if needs_pipeline else ([], None)
    pipeline = pipeline_status(runs) if needs_pipeline else {}
    items = evaluate_compliance(load_compliance_reference(), {
        "health": health, "input_blocked": guard["input_blocked"], "output_checked": guard["output_checked"],
        "traced_count": data["traced_count"], "ci_tests": pipeline.get("tests"),
        "compose_ready": platform_ready(platform), "healing": healing_stats(healing),
    })
    with st.container(key="operations_content"):
        if menu == "운영 개요":
            overview_view(data, guard, health, providers(), items, pipeline, api, server)
        elif menu == "에이전트 처리":
            agent_view(data, guard)
        elif menu == "가드레일":
            guardrail_view(data, guard, server, items)
        elif menu == "안정성·힐링":
            reliability_view(data, guard, health, providers(), reference, healing, server)
        elif menu == "배포 파이프라인":
            pipeline_view(reference, pipeline, runs, runs_error, platform)
        else:
            compliance_view(load_compliance_reference(), items)
