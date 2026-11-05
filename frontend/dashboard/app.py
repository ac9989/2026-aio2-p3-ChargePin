"""Interactive preview of the ChargePin operations dashboard."""
from __future__ import annotations

from copy import deepcopy
from html import escape
from pathlib import Path
import sys

PROJECT_ROOT = str(Path(__file__).resolve().parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
import streamlit as st

from components.styles import show_header, show_metric, show_preview_notice
from components.entry import clear_preview_session
from dashboard.preview_data import AUDIT_EVENTS, DEPLOYMENTS, EVENTS, PROVIDERS

_DASHBOARD_CSS = """
<style>

[data-testid="stMain"] h1 { font-size:1.75rem !important; line-height:1.25; margin-bottom:.35rem; }
[data-testid="stMain"] h3 { font-size:1.12rem !important; line-height:1.35; }
[data-testid="stMain"] h4 { font-size:.96rem !important; line-height:1.4; }
[data-testid="stSidebar"] { border-right:1px solid var(--cp-line); }
[data-testid="stSidebar"] h3 { font-size:1.25rem !important; letter-spacing:-.035em; }
[data-testid="stSidebar"] [data-testid="stRadioGroup"] { gap:6px; width:100%; align-items:stretch; }
[data-testid="stSidebar"] [data-testid="stRadioGroup"] > div { width:100%; }
[class*="st-key-dash_card_"] { background:var(--cp-surface); border:1px solid var(--cp-line) !important; border-radius:18px !important; box-shadow:0 6px 22px #5a3c180b; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] { width:100%; min-height:44px; padding:10px 13px; border:1px solid transparent; border-radius:11px; }
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover { background:#f7eddf; }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] { background:var(--cp-surface); border-color:var(--cp-line); box-shadow:0 3px 10px #5a3c1810; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] p { color:var(--cp-ink); font-size:14px; font-weight:650; }
.dash-nav-label { margin:24px 0 8px; color:var(--cp-muted); font-size:11px; font-weight:800; letter-spacing:.04em; }
.dash-subhead { color:var(--cp-ink); font-size:14px !important; font-weight:750; margin:20px 0 4px; }
[class*="st-key-event_actions_"] div.stButton > button, .st-key-dashboard_back div.stButton > button { min-height:2.1rem; padding:.25rem .7rem; font-size:12px; }
[class*="st-key-event_actions_"] [data-testid="stHorizontalBlock"] { flex-wrap:nowrap; }
.quality-bar { display:flex; height:14px; overflow:hidden; border-radius:999px; background:var(--cp-soft); margin:20px 0 17px; }
.quality-bar span { height:100%; display:block; }
.quality-legend { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px 20px; }
.quality-item { display:flex; align-items:center; gap:8px; color:var(--cp-muted); font-size:12px; }
.quality-item i { width:9px; height:9px; flex:0 0 9px; border-radius:50%; }
.quality-item b { margin-left:auto; color:var(--cp-ink); font-size:13px; }
.chart-total { color:var(--cp-muted); font-size:12px; margin-top:18px; }
.guard-list { display:grid; gap:17px; margin:20px 0 12px; }
.guard-row { display:grid; grid-template-columns:105px minmax(40px,1fr) 30px; align-items:center; gap:9px; font-size:12px; color:var(--cp-ink); }
.guard-track { height:9px; background:var(--cp-soft); border-radius:999px; overflow:hidden; }
.guard-track span { display:block; height:100%; background:#a87348; border-radius:999px; }
.guard-row b { text-align:right; font-size:13px; }
.dash-lead { color:var(--cp-muted); font-size:14px; margin-top:-8px; margin-bottom:18px; line-height:1.6; }
.dash-section { margin:8px 0 4px; font-size:17px; font-weight:800; color:var(--cp-ink); letter-spacing:-.03em; }
.dash-section-note { color:var(--cp-muted); font-size:12px; margin-bottom:10px; line-height:1.5; }
.dash-insight { height:100%; min-height:120px; border:1px solid var(--cp-line); border-radius:15px; background:var(--cp-surface); padding:16px; }
.dash-insight-title { font-size:13px; font-weight:800; color:var(--cp-ink); }
.dash-insight-copy { font-size:13px; line-height:1.5; color:var(--cp-muted); margin-top:8px; }
.dash-tag { display:inline-block; padding:4px 9px; border-radius:999px; background:#e9f1e5; color:#3c6241; font-size:11px; font-weight:800; margin-bottom:8px; }
.dash-tag.attention { background:#faebd3; color:#875315; }
.dash-tag.failed { background:#fae7e1; color:#984f3f; }
.dash-tag.neutral { background:#f1ede8; color:#786a5e; }
.dash-stage { min-height:105px; border:1px solid var(--cp-line); border-radius:14px; background:var(--cp-surface); padding:13px; }
.dash-stage-name { font-weight:800; color:var(--cp-ink); font-size:13px; margin-bottom:9px; }
.dash-stage-meta { color:var(--cp-muted); font-size:12px; }
.dash-context { padding:13px 15px; border:1px solid var(--cp-line); border-radius:13px; background:var(--cp-soft); color:var(--cp-ink); font-size:13px; line-height:1.6; }
.dash-kv { font-size:13px; line-height:1.9; color:var(--cp-ink); }
.dash-page-label { min-width:145px; padding:0 8px; color:var(--cp-muted); font-size:12px; text-align:center; white-space:nowrap; }
[class*="st-key-pagination_"] div.stButton > button { min-height:2.1rem; padding:.2rem .45rem; font-size:13px; }
[class*="st-key-pagination_"] [data-testid="stHorizontalBlock"] { flex-wrap:nowrap; }
.dash-jump { display:flex; flex-wrap:wrap; gap:8px; margin:2px 0 15px; }
.dash-jump a { display:inline-block; padding:7px 12px; border:1px solid var(--cp-line); border-radius:999px; background:var(--cp-surface); color:var(--cp-ink) !important; font-size:13px; font-weight:700; text-decoration:none; }
.dash-jump a:hover { background:var(--cp-soft); }
.dash-kv span { display:inline-block; width:62px; color:var(--cp-muted); }
[data-testid="stSidebar"] [data-testid="stRadioGroup"] { gap:3px; }
</style>
"""


def initialize_state() -> None:
    defaults = {
        "sample_events": EVENTS,
        "sample_audit_events": AUDIT_EVENTS,
    }
    for name, value in defaults.items():
        if name not in st.session_state:
            st.session_state[name] = deepcopy(value)


def show_preview_message(message: str) -> None:
    st.info(message + " 실제 서버에는 요청하지 않았어요.")


def show_section_heading(title: str, note: str = "") -> None:
    st.markdown('<div class="dash-section">' + escape(title) + '</div>', unsafe_allow_html=True)
    if note:
        st.markdown('<div class="dash-section-note">' + escape(note) + '</div>', unsafe_allow_html=True)


def show_insight(label: str, title: str, description: str, tone: str = "") -> None:
    st.markdown(
        '<div class="dash-insight"><span class="dash-tag ' + escape(tone) + '">'
        + escape(label) + '</span><div class="dash-insight-title">' + escape(title)
        + '</div><div class="dash-insight-copy">' + escape(description) + '</div></div>',
        unsafe_allow_html=True,
    )


def render_pages(key_prefix: str, rows: list[dict], page_size: int = 5) -> None:
    page_count = max(1, (len(rows) + page_size - 1) // page_size)
    state_key = f"{key_prefix}_page"
    if state_key not in st.session_state:
        st.session_state[state_key] = 1
    page = min(max(1, st.session_state[state_key]), page_count)
    st.session_state[state_key] = page
    start = (page - 1) * page_size
    if rows:
        st.dataframe(rows[start:start + page_size], width="stretch", hide_index=True, height=min(390, 38 * (min(page_size, len(rows) - start) + 1)))
    else:
        st.markdown('<div class="dash-context">선택한 조건에 해당하는 예시 이력이 없어요.</div>', unsafe_allow_html=True)
    with st.container(
        key=f"pagination_{key_prefix}", horizontal=True,
        horizontal_alignment="center", vertical_alignment="center", gap=None, wrap=False,
    ):
        if st.button("이전", key=f"{key_prefix}_previous", disabled=page <= 1, width=64):
            st.session_state[state_key] = page - 1
            st.rerun()
        st.markdown(
            f'<div class="dash-page-label">{page} / {page_count} 페이지 · 총 {len(rows)}건</div>',
            unsafe_allow_html=True, width="content",
        )
        if st.button("다음", key=f"{key_prefix}_next", disabled=page >= page_count, width=64):
            st.session_state[state_key] = page + 1
            st.rerun()


def show_providers() -> None:
    show_section_heading("외부 API 연결", "출처별 응답 상태와 마지막 성공 시각")
    st.dataframe(PROVIDERS, width="stretch", hide_index=True)


def show_recent_events(prefix: str, show_actions: bool = False) -> None:
    notice = None
    if show_actions:
        title, actions = st.columns([1.2, 1], vertical_alignment="center")
        with title:
            show_section_heading("최근 처리 이벤트", "조회 · 검증 · 재시도 흐름")
        with actions:
            with st.container(key=f"event_actions_{prefix}", horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small", wrap=False):
                if st.button("예시 요청 재처리", key=f"{prefix}_retry", width="content"):
                    notice = "재처리 화면을 선택했습니다."
                if st.button("예시 캐시 갱신", key=f"{prefix}_cache", width="content"):
                    notice = "캐시 갱신 화면을 선택했습니다."
    else:
        show_section_heading("최근 처리 이벤트", "조회 · 검증 · 재시도 흐름")
    if notice:
        show_preview_message(notice)
    render_pages(prefix, st.session_state.sample_events)


def show_overview() -> None:
    st.title("운영 개요")
    st.markdown('<div class="dash-lead">서비스와 배포 흐름에서 먼저 살펴볼 내용을 모았어요.</div>', unsafe_allow_html=True)
    cards = st.columns(4)
    with cards[0]:
        show_metric("요청 성공률", "98.2%")
    with cards[1]:
        show_metric("재시도율", "6.4%")
    with cards[2]:
        show_metric("안전 응답 비율", "3.1%", highlight=True)
    with cards[3]:
        show_metric("최근 배포", "성공")

    show_section_heading("지금 살펴볼 항목", "아래 내용은 화면 구성을 위한 예시입니다.")
    left, middle, right = st.columns(3)
    with left:
        show_insight("연결 지연", "환경공단 충전기", "마지막 성공 이후 응답 지연이 발생했어요.", "attention")
    with middle:
        show_insight("품질 확인", "데이터 지연 5건", "조회한 정보의 시각과 유효성을 확인해요.", "attention")
    with right:
        show_insight("배포 성공", "최근 실행 #104", "테스트부터 동작 확인까지 완료됐어요.")
    with st.container(border=True, key="dash_card_overview_sources"):
        show_providers()
    with st.container(border=True, key="dash_card_overview_events"):
        show_recent_events("recent_events")


def show_quality_chart() -> None:
    items = [
        ("정상", 91, "#8B684B"), ("정보 지연", 5, "#D7AD68"),
        ("수치 이상", 3, "#BE8068"), ("시각 누락", 1, "#B4A599"),
    ]
    total = sum(value for _, value, _ in items)
    segments = "".join(f'<span style="width:{value / total * 100:.2f}%;background:{color}"></span>' for _, value, color in items)
    legends = "".join(
        f'<div class="quality-item"><i style="background:{color}"></i><span>{escape(label)}</span><b>{value}건</b></div>'
        for label, value, color in items
    )
    description = ", ".join(f"{label} {value}건" for label, value, _ in items)
    st.markdown(
        '<div role="img" aria-label="' + escape(description) + '"><div class="quality-bar">'
        + segments + '</div><div class="quality-legend">' + legends
        + f'</div><div class="chart-total">총 {total}건 · 예시</div></div>',
        unsafe_allow_html=True,
    )


def show_guardrail_chart() -> None:
    items = [("입력 조건", 9), ("의심 요청", 7), ("관리자 기능 요청", 2)]
    maximum = max(value for _, value in items)
    rows = "".join(
        '<div class="guard-row"><span>' + escape(label) + '</span>'
        + f'<div class="guard-track"><span style="width:{value / maximum * 100:.2f}%"></span></div><b>{value}건</b></div>'
        for label, value in items
    )
    description = ", ".join(f"{label} {value}건" for label, value in items)
    st.markdown('<div class="guard-list" role="img" aria-label="' + escape(description) + '">' + rows + '</div>', unsafe_allow_html=True)


def show_service_operations() -> None:
    st.title("서비스 운영")
    st.markdown('<div class="dash-lead">외부 연결부터 요청 처리, 데이터 품질까지 이어서 확인해요.</div>', unsafe_allow_html=True)
    left, right = st.columns([1.15, 1])
    with left:
        with st.container(border=True, key="dash_card_service_sources"):
            show_providers()
            st.markdown('<h4 class="dash-subhead">캐시 · 복구</h4>', unsafe_allow_html=True)
            st.caption("서울시 연결 복구 확인 · 환경공단 응답 지연 확인")
    with right:
        with st.container(border=True, key="dash_card_service_agents"):
            show_section_heading("에이전트 · 재시도", "요청 처리 흐름별 상태")
            st.dataframe([
                {"단계": "조건 해석", "상태": "정상", "확인 내용": "검색 조건 확인"},
                {"단계": "데이터 조회", "상태": "지연", "확인 내용": "출처 응답 재확인"},
                {"단계": "결과 검증", "상태": "정상", "확인 내용": "출처와 시각 확인"},
            ], width="stretch", hide_index=True)
            st.markdown('<h4 class="dash-subhead">오류 요약</h4>', unsafe_allow_html=True)
            st.caption("외부 데이터 3건 · 저장소 1건 · 대화 1건")
    left, right = st.columns(2)
    with left:
        with st.container(border=True, key="dash_card_service_quality"):
            show_section_heading("데이터 품질", "정상 · 정보 지연 · 수치 이상 · 시각 누락")
            show_quality_chart()
    with right:
        with st.container(border=True, key="dash_card_service_guardrail"):
            show_section_heading("가드레일", "입력과 응답의 안전성 확인")
            show_guardrail_chart()
            st.caption("대화 원문과 인증 정보는 표시하지 않습니다.")
    with st.container(border=True, key="dash_card_service_events"):
        show_recent_events("service_events", show_actions=True)


def show_deployment_history() -> None:
    st.markdown('<div id="deployment-history"></div>', unsafe_allow_html=True)
    show_section_heading("배포 파이프라인", "실행 이력을 고르면 단계별 결과와 로그를 확인할 수 있어요.")
    counts = st.columns(3)
    with counts[0]:
        show_metric("최근 예시 실행", f"#{DEPLOYMENTS[0]['id']} · {DEPLOYMENTS[0]['result']}")
    with counts[1]:
        show_metric("표시된 예시 실행", f"{len(DEPLOYMENTS)}회")
    with counts[2]:
        show_metric("실패한 예시 실행", f"{sum(run['result'] == '실패' for run in DEPLOYMENTS)}회", highlight=True)

    left, right = st.columns([1.25, 1])
    with left:
        st.markdown("**최근 실행**")
        st.dataframe([
            {"실행": f"#{run['id']}", "시작 시각": run["started"], "결과": run["result"], "소요": run["duration"]}
            for run in DEPLOYMENTS
        ], width="stretch", hide_index=True)
        selected_id = st.selectbox(
            "상세히 볼 실행", [run["id"] for run in DEPLOYMENTS],
            format_func=lambda run_id: next(f"#{run['id']} · {run['result']} · {run['started']}" for run in DEPLOYMENTS if run["id"] == run_id),
            key="deployment_run",
        )
    selected = next(run for run in DEPLOYMENTS if run["id"] == selected_id)
    with right:
        with st.container(border=True):
            st.markdown(f"**선택한 실행 #{selected['id']}**")
            st.caption(selected["summary"])
            st.markdown(
                '<div class="dash-kv"><span>시작</span>' + escape(selected["started"])
                + '<br><span>소요 시간</span>' + escape(selected["duration"])
                + '<br><span>대상</span>' + escape(selected["environment"])
                + '<br><span>브랜치</span>' + escape(selected["branch"])
                + '<br><span>변경본</span>' + escape(selected["commit"])
                + '<br><span>실행 계기</span>' + escape(selected["trigger"]) + '</div>',
                unsafe_allow_html=True,
            )
    show_section_heading("단계별 결과", "건너뛴 단계는 실행되지 않은 상태로 표시해요.")
    columns = st.columns(len(selected["stages"]))
    for number, (column, stage) in enumerate(zip(columns, selected["stages"]), 1):
        tone = "failed" if stage["result"] == "실패" else "neutral" if stage["result"] == "건너뜀" else ""
        with column:
            st.markdown(
                '<div class="dash-stage"><div class="dash-stage-name">' + str(number) + '. ' + escape(stage["name"])
                + '</div><span class="dash-tag ' + tone + '">' + escape(stage["result"])
                + '</span><div class="dash-stage-meta">' + escape(stage["duration"]) + '</div></div>',
                unsafe_allow_html=True,
            )
    stage_name = st.selectbox("로그를 볼 단계", [stage["name"] for stage in selected["stages"]], key="deployment_stage")
    stage = next(stage for stage in selected["stages"] if stage["name"] == stage_name)
    st.caption("아래 로그는 예시이며 GitHub Actions나 배포 서버와 아직 연결되지 않았어요.")
    st.code(stage["log"], language=None)


def show_audit_history() -> None:
    st.markdown('<div id="audit-history"></div>', unsafe_allow_html=True)
    show_section_heading("감사 이력", "누가 어떤 운영 작업을 했는지 확인하는 예시 목록")
    actions = ["전체", "정책 변경", "역할 변경", "요청 재처리", "캐시 갱신", "이력 조회"]
    action = st.selectbox("작업 유형", actions, key="audit_filter")
    rows = [event for event in st.session_state.sample_audit_events if action == "전체" or event["작업"] == action]
    render_pages("audit_events", rows, page_size=10)
    st.caption("이력은 화면 예시입니다. 실제 감사 기록과 조회 권한은 백엔드 연결 후 확인할 수 있어요.")


def show_deploy_and_audit() -> None:
    st.title("배포 · 감사 이력")
    st.markdown('<div class="dash-lead">배포 실행을 자세히 살펴보고, 운영 작업의 변경 이력도 함께 확인해요.</div>', unsafe_allow_html=True)
    st.markdown(
        '<nav class="dash-jump" aria-label="배포와 감사 이력 바로가기">'
        '<a href="#deployment-history" target="_self">배포 파이프라인 ↓</a>'
        '<a href="#audit-history" target="_self">감사 이력 ↓</a></nav>',
        unsafe_allow_html=True,
    )
    show_deployment_history()
    st.divider()
    show_audit_history()



def main() -> None:
    initialize_state()
    with st.sidebar:
        st.markdown("### 운영 대시보드")
        st.caption("서비스 상태와 운영 이력을 한눈에 확인해요.")
        st.markdown('<div class="dash-nav-label">운영 메뉴</div>', unsafe_allow_html=True)
        menu_options = ["운영 개요", "서비스 운영", "배포 · 감사 이력"]
        menu = st.radio("메뉴", menu_options, label_visibility="collapsed", key="dashboard_menu", width="stretch")
    brand, back = st.columns([6, 4], vertical_alignment="center")
    with brand:
        show_header("ChargePin 운영 대시보드", "서비스 상태부터 배포 이력까지")
    with back:
        with st.container(key="dashboard_actions", horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small", wrap=True):
            if st.button("← 사용자 화면", key="dashboard_back", width="content"):
                st.session_state.active_view = "user"
                st.rerun()
            st.button("⏻", key="dashboard_logout", width=46, help="현재 접속을 마칩니다.", on_click=clear_preview_session)
    show_preview_notice(admin=True)
    if menu == "운영 개요":
        show_overview()
    elif menu == "서비스 운영":
        show_service_operations()
    else:
        show_deploy_and_audit()


def render_dashboard() -> None:
    if not st.session_state.get("entry_granted", False) or st.session_state.get("entry_role") != "admin":
        st.error("관리자 권한이 필요한 화면이에요.")
        return
    st.markdown(_DASHBOARD_CSS, unsafe_allow_html=True)
    main()


if __name__ == "__main__":
    st.set_page_config(page_title="ChargePin", page_icon="⚡", layout="wide", initial_sidebar_state="auto")
    from user_app import launch
    launch()
