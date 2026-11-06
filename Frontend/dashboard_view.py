"""ChargePin operations dashboard, driven by observed session events."""
from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
from typing import Any, Callable

import altair as alt
import pandas as pd
import requests
import streamlit as st

from dashboard_data import KST, allowed_demo_role_transitions, can_manage_roles, display_time, summarize_events, event_time
from api_client import ApiError

AMBER = "#C8940B"
DARK = "#252B32"
MUTED = "#74808C"
GRID = "#EBEEF1"


def label(text: Any) -> str:
    return escape(str(text), quote=True)


def section_title(title: str, subtitle: str = "") -> None:
    note = '<span class="cp-section-note">' + label(subtitle) + '</span>' if subtitle else ""
    st.markdown('<div class="cp-section-title"><h3>' + label(title) + '</h3>' + note + '</div>',
                unsafe_allow_html=True)


def empty_chart(message: str = "데이터 연결 대기") -> None:
    st.markdown('<div class="cp-chart-empty"><span class="cp-empty-icon">—</span><span>'
                + label(message) + '</span></div>', unsafe_allow_html=True)


def metric_card(title: str, value: str, detail: str, tone: str = "neutral", link: str | None = None) -> None:
    icons = {
        "API 요청": '<path d="M5 6h14v12H5zM8 10h8M8 14h5"/><path d="m16 13 2 1-2 1"/>',
        "부분 응답 · 실패": '<path d="M12 3 3 20h18L12 3zM12 9v5m0 3h.01"/>',
        "요청 실패": '<path d="M12 3 3 20h18L12 3zM12 9v5m0 3h.01"/>',
        "백엔드 헬스": '<path d="M3 12h4l2-5 3 10 3-6h6"/>',
        "백엔드 연결": '<path d="M3 12h4l2-5 3 10 3-6h6"/>',
        "최근 GitHub 실행": '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 6h8m2 2v8"/>',
        "최근 실행": '<circle cx="6" cy="6" r="2"/><circle cx="18" cy="6" r="2"/><circle cx="18" cy="18" r="2"/><path d="M8 6h8m2 2v8"/>',
        "장소 조회": '<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/>',
        "챗 해석": '<path d="M4 5h16v11H9l-5 4V5z"/><path d="m10 10 2-2 2 2-2 2z"/>',
        "충전소 검색": '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>',
        "검색 평균 응답": '<circle cx="12" cy="12" r="8"/><path d="M12 7v5l4 2"/>',
        "자동 복구": '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M6 9a7 7 0 0 1 12-2l2 5M4 12l2 5a7 7 0 0 0 12-2"/>',
        "테스트 결과": '<path d="M8 4h8v3H8zM6 5H4v16h16V5h-4M8 13l2 2 5-5"/>',
        "이미지 게시": '<path d="m12 3 8 4.5v9L12 21l-8-4.5v-9zM4 7.5l8 4.5 8-4.5M12 12v9"/><path d="M12 3v4m-2-2 2-2 2 2"/>',
        "EC2 배포": '<rect x="4" y="5" width="16" height="6" rx="2"/><rect x="4" y="13" width="16" height="6" rx="2"/><path d="M8 8h.01M8 16h.01M12 8h5M12 16h5"/>',
    }
    icon = icons.get(title, '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/>')
    svg = '<span class="cp-metric-icon"><svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + icon + '</svg></span>'
    st.markdown(
        '<div class="cp-metric">' + svg + '<div class="cp-metric-content"><div class="cp-metric-title-row"><span class="cp-metric-title">' + label(title)
        + '</span>' + ('<a class="cp-reference-link" href="' + label(link) + '" target="_self">배포·운영 관리표 ↗</a>' if link else '')
        + '</div><div class="cp-metric-value">' + label(value)
        + '</div><span class="cp-metric-sub ' + label(tone) + '">' + label(detail) + '</span></div></div>',
        unsafe_allow_html=True,
    )


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
    st.altair_chart(chart.configure_view(stroke=None).configure_axis(
        labelColor=MUTED, titleColor=MUTED, gridColor=GRID, domainColor=GRID,
        labelFontSize=13, titleFontSize=13), width="stretch", theme=None)


def bar_chart(data: list[dict[str, Any]], empty: str) -> None:
    if not data:
        empty_chart(empty)
        return
    frame = pd.DataFrame(data)
    chart = (alt.Chart(frame).mark_bar(color=DARK, cornerRadiusEnd=5, height=17).encode(
        y=alt.Y("kind:N", title=None, sort=None, axis=alt.Axis(labelLimit=100)),
        x=alt.X("count:Q", title="건", scale=alt.Scale(zero=True),
                axis=alt.Axis(grid=True, tickMinStep=1, format="d")),
        tooltip=[alt.Tooltip("kind:N", title="요청"), alt.Tooltip("count:Q", title="건수", format="d")],
    ).properties(height=172))
    st.altair_chart(chart.configure_view(stroke=None).configure_axis(
        labelColor=MUTED, titleColor=MUTED, gridColor=GRID, domainColor=GRID,
        labelFontSize=13, titleFontSize=13), width="stretch", theme=None)


def donut_chart(data: list[dict[str, Any]]) -> None:
    if not data:
        empty_chart("요청이 기록되면 비중을 표시해요")
        return
    frame = pd.DataFrame(data)
    chart = (alt.Chart(frame).mark_arc(innerRadius=56, outerRadius=88).encode(
        theta=alt.Theta("count:Q", stack=True),
        color=alt.Color("kind:N", title="요청 유형",
                        scale=alt.Scale(domain=["장소 조회", "챗 해석", "직접 검색", "챗 검색"],
                                        range=["#2D333A", "#D5A11B", "#98A6B1", "#607382"]),
        legend=alt.Legend(orient="right", labelLimit=140)),
        tooltip=[alt.Tooltip("kind:N", title="요청"), alt.Tooltip("count:Q", title="건수", format="d")],
    ).properties(height=190))
    st.altair_chart(chart.configure_view(stroke=None).configure_legend(
        labelColor=MUTED, titleColor=MUTED, labelFontSize=13, titleFontSize=13), width="stretch", theme=None)


def provider_rows(states: list[tuple[str, str]], limit: int | None = None) -> None:
    rows = []
    for name, value in states[:limit]:
        # A key or an HTTP response does not prove upstream availability.
        tone = "bad" if "실패" in value or "미설정" in value else "muted"
        rows.append('<div class="cp-provider-row"><span>' + label(name)
                    + '</span><span class="cp-provider-status ' + tone + '"><i></i>' + label(value) + '</span></div>')
    st.markdown('<div class="cp-provider-list">' + "".join(rows) + '</div>', unsafe_allow_html=True)


def request_rows(observed: list[dict[str, Any]]) -> None:
    if not observed:
        empty_chart("현재 세션의 요청 기록이 없어요")
        return
    rows = []
    for item in reversed(observed[-5:]):
        elapsed = "—" if item["elapsed_ms"] is None else f'{item["elapsed_ms"]:,.0f} ms'
        tone = "bad" if item["state"] == "실패" else "warn" if item["state"] == "부분 응답" else "neutral"
        rows.append('<div class="cp-event-row"><span>' + label(display_time(item["time"])) + '</span><b>'
                    + label(item["kind"]) + '</b><span class="cp-event-state ' + tone + '">'
                    + label(item["state"]) + '</span><span>' + label(elapsed) + '</span></div>')
    st.markdown('<div class="cp-event-list">' + "".join(rows) + '</div>', unsafe_allow_html=True)


def request_history_table(observed: list[dict[str, Any]]) -> None:
    if not observed:
        st.caption("현재 세션의 요청 기록이 없어요.")
        return
    records = [{
        "시각 (KST)": display_time(item["time"], full=True),
        "요청": item["kind"], "결과": item["state"],
        "소요 (ms)": item["elapsed_ms"],
        "요청 ID": item.get("request_id") or "—",
    } for item in reversed(observed[-20:])]
    st.dataframe(pd.DataFrame(records), hide_index=True, width="stretch", height=240)


def pipeline_snapshot(reference: dict[str, Any], compact: bool = False) -> None:
    stages = reference.get("stages", [])
    if not stages:
        empty_chart()
        return
    parts = []
    for index, stage in enumerate(stages, start=1):
        mode = stage.get("mode", "확인 필요")
        parts.append('<div class="cp-pipeline-step"><span class="cp-pipeline-index">'
                     + f'{index:02d}' + '</span><div><b>' + label(stage.get("title", "단계"))
                     + '</b><small>' + label(mode) + '</small></div></div>')
    st.markdown('<div class="cp-pipeline ' + ("compact" if compact else "")
                + '">' + "".join(parts) + '</div>', unsafe_allow_html=True)


def app_topbar(title: str) -> None:
    scope = ("요청 · 서비스 안정성 · 빌드/배포 통합 요약" if title == "운영 현황" else
             "관리표 기록과 실시간 연동 상태" if title == "빌드·배포" else "현재 세션 · 최근 100건")
    st.markdown('<div class="cp-dashboard-title"><span></span><h2>' + label(title)
                + '</h2></div><div class="cp-dashboard-subtitle">' + label(scope) + '</div>',
                unsafe_allow_html=True)


def overview_summary(title: str, scope: str, values: list[tuple[str, str]],
                     note: str, tone: str = "neutral") -> None:
    fields = "".join('<div class="cp-summary-field"><span>' + label(key)
                     + '</span><strong>' + label(value) + '</strong></div>' for key, value in values)
    st.markdown('<section class="cp-summary-panel"><div class="cp-summary-header"><h3>'
                + label(title) + '</h3><span>' + label(scope) + '</span></div>'
                '<div class="cp-summary-fields ' + label(tone) + '">' + fields + '</div>'
                '<div class="cp-summary-note">' + label(note) + '</div></section>', unsafe_allow_html=True)


def overview(data: dict[str, Any], health: str, providers: list[tuple[str, str]], reference: dict[str, Any]) -> None:
    counts = {item["kind"]: item["count"] for item in data["kind_counts"]}
    choices = ["요청 정보", "서비스 안정성", "빌드·배포"]
    if st.session_state.get("overview_axis") not in choices:
        st.session_state.overview_axis = choices[0]
    selected = st.radio(
        "운영 개요 항목", choices, key="overview_axis", horizontal=True,
        label_visibility="collapsed", width="stretch",
    )
    location_status = next((value for name, value in providers if name == "카카오 장소"), "조회 정보 없음")
    if "응답 수신" in location_status:
        location_summary = "카카오 장소 · 응답 수신"
    elif "후보 수신" in location_status:
        location_summary = "카카오 장소 · 후보 확인"
    elif "실패" in location_status:
        location_summary = "카카오 장소 · 요청 실패"
    else:
        location_summary = "카카오 장소 · 조회 기록 없음"
    if selected == "요청 정보":
        overview_summary("요청 정보 요약", "현재 세션 · 최근 100건",
                         [("충전소 검색", f'{data["search_count"]:,}건'),
                          ("장소 조회", f'{counts.get("장소 조회", 0):,}건'),
                          ("AI 챗 요청", f'{counts.get("챗 해석", 0):,}건')],
                         "요청별 흐름과 최근 이력은 상단 요청 정보 메뉴에서 확인할 수 있어요.")
        with st.container(border=True):
            section_title("요청 추이", "현재 세션 · 건")
            line_chart(data["minute_counts"], "count", "건", "요청이 기록되면 표시돼요")
    elif selected == "서비스 안정성":
        tone = "good" if health == "정상" else "bad" if health == "연결 불가" else "warn"
        overview_summary("서비스 안정성 요약", "현재 세션 · 최근 확인",
                         [("백엔드 헬스", health), ("부분 응답", f'{data["partial_count"]:,}건'),
                          ("검색 실패", f'{data["failure_count"]:,}건')],
                         location_summary, tone)
        with st.container(border=True):
            section_title("최근 확인이 필요한 요청", "현재 세션 · 최근 100건")
            issues = [item for item in reversed(data["searches"]) if item["state"] in ("부분 응답", "실패")]
            if issues:
                records = [{"시각": display_time(item["time"], full=True), "요청": item["kind"],
                            "결과": item["state"], "응답 시간": f'{item["elapsed_ms"]:,} ms' if item["elapsed_ms"] is not None else "확인 필요",
                            "요청 ID": item["request_id"] or "확인 필요"} for item in issues[:5]]
                st.dataframe(pd.DataFrame(records), hide_index=True, width="stretch")
                st.caption("현재 세션에서 관측한 결과이며, 원인과 서버 전체 상태는 별도 로그 연결이 필요합니다.")
            else:
                empty_chart("현재 세션에 부분 응답이나 검색 실패 기록이 없어요" if data["search_count"] else "검색 요청이 기록되면 표시돼요")
    else:
        runs, runs_error = github_runs()
        latest = runs[0] if runs else {}
        result = {"success": "성공", "failure": "실패", "cancelled": "취소"}.get(latest.get("conclusion"), "진행 중" if latest else "확인 필요")
        overview_summary("빌드·배포 요약", "GitHub 최근 실행 · 관리표 기록",
                         [("최근 실행", result), ("이미지", "GHCR"), ("EC2 배포", "수동")],
                         runs_error or "실행 결과는 GitHub Actions, 배포 방식은 관리표 기준이에요.")
        if runs:
            counts = {}
            for run in runs:
                state = run.get("conclusion") or run.get("status") or "확인 필요"
                counts[state] = counts.get(state, 0) + 1
            with st.container(border=True):
                section_title("최근 실행 결과", "최근 최대 20건")
                bar_chart([{"kind": key, "count": value} for key, value in counts.items()], "실행 이력이 없어요")



def overview_dashboard(data: dict[str, Any], health: str,
                      providers: list[tuple[str, str]]) -> None:
    """Show observed request, stability, and deployment signals together."""
    counts = {item["kind"]: item["count"] for item in data["kind_counts"]}
    issue_count = data["partial_count"] + data["failure_count"]
    health_tone = "good" if health == "정상" else "bad" if health == "연결 불가" else "warn"
    runs, runs_error = github_runs()
    latest = runs[0] if runs else {}
    conclusion = latest.get("conclusion")
    run_state = {"success": "성공", "failure": "실패", "cancelled": "취소"}.get(
        conclusion, "진행 중" if latest and latest.get("status") == "in_progress" else
        "진행 중" if latest else "확인 필요")
    if latest and not conclusion and latest.get("status") not in ("in_progress", "queued"):
        run_state = "결과 확인 필요"
    run_tone = "good" if run_state == "성공" else "bad" if run_state == "실패" else "warn"
    branch = str(latest.get("head_branch") or "브랜치 정보 없음")

    cards = [
        ("API 요청", f'{len(data["observed"]):,}건',
         f'장소 조회 {counts.get("장소 조회", 0):,} · 검색 {data["search_count"]:,}', "neutral"),
        ("부분 응답 · 실패", f'{issue_count:,}건',
         f'부분 응답 {data["partial_count"]:,} · 실패 {data["failure_count"]:,}', "warn" if issue_count else "good"),
        ("백엔드 헬스", health, "/healthz 현재 확인", health_tone),
        ("최근 GitHub 실행", run_state,
         branch if latest else ("GitHub 연결 확인 필요" if runs_error else "실행 이력 없음"), run_tone),
    ]
    with st.container(key="overview_metrics"):
        for col, item in zip(st.columns(4, gap="medium"), cards):
            with col:
                metric_card(*item)

    with st.container(key="overview_charts"):
        left, right = st.columns([1.25, 1], gap="medium")
        with left:
            with st.container(border=True, key="overview_request_trend"):
                section_title("요청 추이", "선택 기간 · 분 단위")
                line_chart(data["minute_counts"], "count", "건", "선택 기간에 기록된 검색 요청이 없습니다.")
        with right:
            with st.container(border=True, key="overview_request_mix"):
                section_title("요청 구성", "장소 조회 · AI · 직접 검색")
                donut_chart(data["kind_counts"])

    with st.container(key="overview_details"):
        request_col, stability_col, deploy_col = st.columns([1.1, 1, 1], gap="medium")
        with request_col:
            with st.container(border=True, key="overview_recent_requests"):
                section_title("최근 요청", "최대 5건 · KST")
                request_rows(data["observed"])
                st.caption(f'검색 평균 응답 시간: {data["average_ms"]:,} ms' if data["average_ms"] is not None
                           else "응답 시간 데이터가 아직 없습니다.")
        with stability_col:
            with st.container(border=True, key="overview_stability"):
                section_title("서비스 안정성", "현재 확인 결과")
                provider_rows([("백엔드 헬스", health), *providers])
                st.caption("외부 API는 최근 관측 결과와 설정 여부를 표시합니다.")
        with deploy_col:
            with st.container(border=True, key="overview_deployment"):
                section_title("빌드 · 배포", "GitHub 실시간 · EC2 수동 확인")
                run_time = display_time(event_time(latest.get("created_at")), full=True) if latest else "실행 기록 확인 필요"
                provider_rows([
                    ("최근 Actions", run_state),
                    ("브랜치", branch),
                    ("실행 시각", run_time),
                    ("EC2 배포", "수동 확인 필요"),
                ])
                if runs_error:
                    st.caption(runs_error)
                elif latest.get("html_url"):
                    st.link_button("GitHub Actions 실행 보기", latest["html_url"], use_container_width=True)
                st.link_button("배포 · 운영 관리표", "https://docs.google.com/spreadsheets/d/1REaJ0qNf6k_KcAHylli05kOVM_SWHloR/edit?gid=853363652#gid=853363652",
                               use_container_width=True)

def flow_view(data: dict[str, Any]) -> None:
    counts = {row["kind"]: row["count"] for row in data["kind_counts"]}
    kpis = [
        ("장소 조회", f'{counts.get("장소 조회", 0):,}건', "현재 세션", "neutral"),
        ("챗 해석", f'{counts.get("챗 해석", 0):,}건', "현재 세션", "neutral"),
        ("충전소 검색", f'{data["search_count"]:,}건', "직접 검색 + 챗 검색", "neutral"),
        ("부분 응답 · 실패", f'{data["partial_count"] + data["failure_count"]:,}건', "현재 세션", "warn" if data["partial_count"] + data["failure_count"] else "neutral"),
    ]
    with st.container(key="flow_kpis"):
        for col, item in zip(st.columns(4, gap="medium"), kpis):
            with col:
                metric_card(*item)
    with st.container(key="flow_charts"):
        left, right = st.columns([1.2, 1], gap="medium")
        with left:
            with st.container(border=True, key="flow_trend"):
                section_title("검색 요청 추이", "건 · 현재 세션")
                line_chart(data["minute_counts"], "count", "건", "검색 요청을 기다리는 중이에요")
        with right:
            with st.container(border=True, key="flow_donut"):
                section_title("요청 구성", "건 · 현재 세션")
                donut_chart(data["kind_counts"])
    with st.container(key="flow_details"):
        left, right = st.columns([1.2, 1], gap="medium")
        with left:
            with st.container(border=True, key="flow_events"):
                section_title("최근 요청", "최대 5건 · KST")
                request_rows(data["observed"])
        with right:
            with st.container(border=True, key="flow_handoff"):
                section_title("처리 단계")
                st.markdown(
                    '<div class="cp-flow-pills"><span>요청</span><i>›</i><span>계획</span><i>›</i>'
                    '<span>조회</span><i>›</i><span>검증</span><i>›</i><span>응답</span></div>'
                    '<div class="cp-inline-note">에이전트별 처리 이력 · Handoff 연결 대기</div>',
                    unsafe_allow_html=True)
    with st.expander("요청 이력 자세히", expanded=False):
        st.caption("현재 세션 · 최근 20건 · 소요 시간은 프론트 왕복 기준")
        request_history_table(data["observed"])


def system_view(data: dict[str, Any], health: str, providers: list[tuple[str, str]]) -> None:
    elapsed = "—" if data["average_ms"] is None else f'{data["average_ms"]:,} ms'
    cards = [
        ("백엔드 연결", health, "/healthz 응답", "good" if health == "정상" else "bad" if health == "연결 불가" else "warn"),
        ("검색 평균 응답", elapsed, "프론트 왕복 · 현재 세션", "neutral"),
        ("요청 실패", f'{data["failure_count"]:,}건', "검색 요청 · 현재 세션", "bad" if data["failure_count"] else "neutral"),
        ("자동 복구", "연결 대기", "감지 · 조치 이력", "neutral"),
    ]
    with st.container(key="system_kpis"):
        for col, item in zip(st.columns(4, gap="medium"), cards):
            with col:
                metric_card(*item, link="https://docs.google.com/spreadsheets/d/1REaJ0qNf6k_KcAHylli05kOVM_SWHloR/edit?gid=853363652#gid=853363652" if item[0] == "EC2 배포" else None)
    with st.container(key="system_charts"):
        left, right = st.columns([1.2, 1], gap="medium")
        with left:
            with st.container(border=True, key="system_latency"):
                section_title("검색 응답 시간", "ms · 프론트 왕복 · 현재 세션")
                points = [{"time": item["time"].isoformat(), "elapsed_ms": item["elapsed_ms"]}
                          for item in data["searches"] if item["elapsed_ms"] is not None]
                line_chart(points, "elapsed_ms", "ms", "검색 응답 시간이 기록되면 표시해요")
        with right:
            with st.container(border=True, key="system_sources"):
                section_title("외부 연결", "키 설정 · 세션 응답")
                provider_rows(providers)
    with st.container(key="system_details"):
        left, right = st.columns(2, gap="medium")
        with left:
            with st.container(border=True, key="system_recovery"):
                section_title("재시도 · 복구")
                st.markdown('<div class="cp-inline-note">감지 시각 · 재시도 원인 · 복구 소요 시간 · 수동 개입</div>',
                            unsafe_allow_html=True)
                empty_chart("복구 이력 연결 대기")
        with right:
            with st.container(border=True, key="system_quality"):
                section_title("데이터 품질")
                st.markdown('<div class="cp-inline-note">정보 지연 · 누락 · 응답 검증</div>', unsafe_allow_html=True)
                empty_chart("품질 집계 연결 대기")
    with st.expander("연결 · 장애 상세", expanded=False):
        st.caption("원천 API별 재시도와 복구 이력은 서버 관측 정보 연결 후 표시합니다.")
        provider_rows(providers)
        st.markdown('<div class="cp-inline-note">회로 상태 · 재시도 원인 · 수동 조치 · 감사 이력: 연결 대기</div>',
                    unsafe_allow_html=True)


@st.cache_data(ttl=120, show_spinner=False)
def github_runs() -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = requests.get(
            "https://api.github.com/repos/ac9989/2026-aio2-p3-ChargePin/actions/runs",
            params={"per_page": 20}, headers={"Accept": "application/vnd.github+json"}, timeout=6)
        if response.status_code != 200:
            return [], f"GitHub 응답 {response.status_code} · 저장소 공개 여부와 접근 권한을 확인해 주세요."
        return response.json().get("workflow_runs", []), None
    except (requests.RequestException, ValueError):
        return [], "GitHub 실행 이력을 불러오지 못했어요."



@st.cache_data(ttl=120, show_spinner=False)
def github_jobs(run_id: int) -> tuple[list[dict[str, Any]], str | None]:
    try:
        response = requests.get(
            f"https://api.github.com/repos/ac9989/2026-aio2-p3-ChargePin/actions/runs/{run_id}/jobs",
            params={"per_page": 100},
            headers={"Accept": "application/vnd.github+json"}, timeout=6)
        if response.status_code != 200:
            return [], f"작업 조회 실패 · HTTP {response.status_code}"
        return response.json().get("jobs", []), None
    except (requests.RequestException, ValueError):
        return [], "작업 이력을 불러오지 못했어요."


@st.cache_data(ttl=120, show_spinner=False)
def latest_main_run() -> tuple[dict[str, Any] | None, str | None]:
    try:
        response = requests.get(
            "https://api.github.com/repos/ac9989/2026-aio2-p3-ChargePin/actions/workflows/ci.yml/runs",
            params={"branch": "main", "event": "push", "per_page": 1},
            headers={"Accept": "application/vnd.github+json"}, timeout=6)
        if response.status_code != 200:
            return None, f"main 실행 조회 실패 · HTTP {response.status_code}"
        runs = response.json().get("workflow_runs", [])
        return (runs[0] if runs else None), None
    except (requests.RequestException, ValueError):
        return None, "main 실행 이력을 불러오지 못했어요."


def job_status(job: dict[str, Any] | None) -> str:
    if not job:
        return "확인 필요"
    if job.get("status") != "completed":
        return "진행 중"
    return {"success": "성공", "failure": "실패", "cancelled": "취소",
            "skipped": "건너뜀", "timed_out": "시간 초과"}.get(job.get("conclusion"), "확인 필요")


def ci_card_status(runs: list[dict[str, Any]]) -> tuple[str, str, str, str]:
    latest_ci = next((run for run in runs if run.get("name") == "ChargePin CI"), None)
    tests, test_detail = "확인 필요", "최근 CI 작업 없음"
    if latest_ci and isinstance(latest_ci.get("id"), int):
        jobs, error = github_jobs(latest_ci["id"])
        expected = {"Backend unit tests", "Frontend syntax check", "Existing Auto Healing policy tests"}
        found = [job for job in jobs if job.get("name") in expected]
        states = [job_status(job) for job in found]
        if error:
            tests, test_detail = "조회 실패", error
        elif len(found) != len(expected):
            tests, test_detail = "확인 필요", "테스트 작업 정보가 불완전합니다"
        else:
            tests = ("실패" if any(state in ("실패", "시간 초과") for state in states)
                     else "진행 중" if "진행 중" in states
                     else "성공" if all(state == "성공" for state in states)
                     else "확인 필요")
            test_detail = f"CI #{latest_ci.get('run_number', '—')} · {latest_ci.get('head_branch', '—')} · 테스트·문법 검사"

    main_run, error = latest_main_run()
    published, publish_detail = "확인 필요", error or "main 게시 실행 없음"
    if main_run and isinstance(main_run.get("id"), int):
        jobs, error = github_jobs(main_run["id"])
        job = next((item for item in jobs if item.get("name") == "Publish both images to GHCR (main only)"), None)
        published = "조회 실패" if error else job_status(job)
        publish_detail = error or f"main CI #{main_run.get('run_number', '—')} · GHCR 게시 작업"
    return tests, test_detail, published, publish_detail


def cicd_view(reference: dict[str, Any]) -> None:

    reference_date = str(reference.get("source_date", "확인 필요"))
    runs, runs_error = github_runs()
    latest = runs[0] if runs else {}
    tests, test_detail, published, publish_detail = ci_card_status(runs)
    recent = {"success": "성공", "failure": "실패", "cancelled": "취소"}.get(latest.get("conclusion"), "진행 중" if latest else "연결 대기")
    cards = [
        ("최근 실행", recent, "GitHub Actions", "neutral"),
        ("테스트 결과", tests, test_detail, "good" if tests == "성공" else "bad" if tests == "실패" else "neutral"),
        ("이미지 게시", published, publish_detail, "good" if published == "성공" else "bad" if published == "실패" else "neutral"),
        ("EC2 배포", "수동", "관리표 기록 · " + reference_date, "neutral"),
    ]
    with st.container(key="pipeline_kpis"):
        for col, item in zip(st.columns(4, gap="medium"), cards):
            with col:
                metric_card(*item, link="https://docs.google.com/spreadsheets/d/1REaJ0qNf6k_KcAHylli05kOVM_SWHloR/edit?gid=853363652#gid=853363652" if item[0] == "EC2 배포" else None)
    with st.container(border=True, key="pipeline_flow"):
        section_title("배포 흐름", "관리표 기록 · " + reference_date + " · 실시간 아님")
        pipeline_snapshot(reference)
    with st.container(key="pipeline_details"):
        left, right = st.columns([1.2, 1], gap="medium")
        with left:
            with st.container(border=True, key="pipeline_runs"):
                section_title("최근 실행", "시각 · 브랜치 · 결과 · 소요 시간")
                if runs_error:
                    st.info(runs_error)
                elif not runs:
                    empty_chart("실행 이력이 없어요")
                else:
                    records = []
                    for run in runs[:8]:
                        records.append({"워크플로": run.get("name", "—"), "브랜치": run.get("head_branch", "—"),
                                        "상태": run.get("conclusion") or run.get("status") or "—",
                                        "시작 시각": display_time(event_time(run.get("created_at")), full=True)})
                    st.dataframe(pd.DataFrame(records), hide_index=True, width="stretch")
                    st.link_button("GitHub Actions에서 보기", "https://github.com/ac9989/2026-aio2-p3-ChargePin/actions")
        with right:
            with st.container(border=True, key="pipeline_checks"):
                section_title("검증 · 복구", "관리표 기록 · " + reference_date)
                rows = []
                for check in reference.get("checks", [])[:4]:
                    rows.append('<div class="cp-provider-row"><span>' + label(check.get("title", ""))
                                + '</span><span class="cp-check-tag">' + label(check.get("status", "확인 필요"))
                                + '</span></div>')
                st.markdown('<div class="cp-provider-list">' + "".join(rows) + '</div>', unsafe_allow_html=True)
    with st.container(border=True, key="pipeline_logs"):
        section_title("실행 상세 · 로그")
        st.markdown('<div class="cp-inline-note">실패 단계 · 차단 여부 · 알림 · 복구 이력 연결 대기</div>',
                    unsafe_allow_html=True)
    with st.expander("단계별 관리표 기록", expanded=False):
        st.caption("관리표 기준 " + reference_date + " · 실시간 실행 결과가 아닙니다.")
        rows = [{"단계": stage.get("title", "—"), "방식": stage.get("mode", "—"),
                 "기록": stage.get("status", "—"), "내용": stage.get("detail", "—")}
                for stage in reference.get("stages", [])]
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", height=240)
        else:
            st.caption("표시할 기록이 없습니다.")
        more = [{"검증 항목": item.get("title", "—"), "기록": item.get("status", "—"),
                 "내용": item.get("detail", "—")} for item in reference.get("checks", [])]
        if more:
            st.dataframe(pd.DataFrame(more), hide_index=True, width="stretch", height=260)


@st.dialog("상급 관리자 전용 기능입니다")
def senior_only_dialog() -> None:
    st.write("권한 정보는 상급 관리자만 확인할 수 있어요.")


@st.dialog("권한 관리")
def role_management_dialog() -> None:
    st.markdown(
        '<div class="cp-role-list">'
        '<div class="cp-role-item"><span class="cp-role-symbol">01</span><div><strong>일반 사용자</strong><p>충전소 탐색 · AI 챗</p></div></div>'
        '<div class="cp-role-item"><span class="cp-role-symbol">02</span><div><strong>하급 관리자</strong><p>운영 대시보드 조회</p></div></div>'
        '<div class="cp-role-item"><span class="cp-role-symbol">03</span><div><strong>상급 관리자</strong><p>운영 대시보드 · 권한 안내 조회</p></div></div>'
        '</div><div class="cp-role-note">운영 기능은 백엔드 연결 상태에 따라 사용할 수 있어요.</div>',
        unsafe_allow_html=True)


def retry_policy_dialog() -> None:
    st.write("재시도 정책 조회와 변경 기능을 연결하면 설정할 수 있어요.")
    st.radio("재시도 횟수", ["1회", "2회", "3회"], horizontal=True, disabled=True)
    st.button("저장", disabled=True, width="stretch")


@st.dialog("운영 기능 연결 대기")
def operations_pending_dialog() -> None:
    st.write("이 기능은 운영 API 연결 후 사용할 수 있어요.")


def management_menu() -> None:
    if st.button("권한 관리", icon=":material/admin_panel_settings:", key="menu_roles", help="권한 관리"):
        if can_manage_roles(st.session_state.get("role")):
            role_management_dialog()
        else:
            senior_only_dialog()


def render_operations_dashboard(api: Any, header: Callable[..., str | None],
                                providers: Callable[[], list[tuple[str, str]]],
                                reference_loader: Callable[[], dict[str, Any]]) -> None:
    def navigation() -> str | None:
        with st.container(key="header_menu", width="stretch"):
            current = st.radio("운영 메뉴", ["운영 개요", "요청 정보", "서비스 안정성", "빌드·배포"],
                               horizontal=True, label_visibility="collapsed", key="dashboard_navigation")

        return current

    with st.container(key="dashboard_header"):
        menu = header(dashboard_view=True, navigation=navigation)
    try:
        result = api.health()
        health = "정상" if result.get("status") == "ok" else "확인 필요"
    except ApiError:
        health = "연결 불가"
    heading = {"운영 개요": "운영 현황", "요청 정보": "요청 정보",
               "서비스 안정성": "서비스 안정성", "빌드·배포": "빌드·배포"}.get(menu, "운영 현황")
    with st.container(key="dashboard_page_heading"):
        title_col, toolbar_col = st.columns([1, 3], gap="small", vertical_alignment="center")
        with title_col:
            app_topbar(heading)
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
    events = [event for event in st.session_state.get("api_events", []) if event_time(event.get("observed_at")) is not None and event_time(event.get("observed_at")) >= cutoff]
    data = summarize_events(events)
    states = providers()
    reference = reference_loader()
    with st.container(key="operations_content"):
        if menu == "운영 개요":
            overview_dashboard(data, health, states)
        elif menu == "요청 정보":
            flow_view(data)
        elif menu == "서비스 안정성":
            system_view(data, health, states)
        else:
            cicd_view(reference)
