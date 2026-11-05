"""Shared presentation helpers for the user interface and dashboard."""
from __future__ import annotations

from html import escape
from typing import Any
import streamlit as st

_PALETTES = {
    "honey": """
    :root {
      --cp-page:#F7F9FB; --cp-surface:#FFFFFF; --cp-soft:#F1F4F7;
      --cp-ink:#202A35; --cp-muted:#6D7986; --cp-line:#E2E8ED;
      --cp-accent:#F5CB46; --cp-accent-hover:#E9BA2C; --cp-action:#252E38;
      --cp-action-text:#FFFFFF; --cp-sidebar:#F2F5F7; --cp-logo:#F8D34D;
      --cp-notice:#FFFBEB; --cp-notice-line:#F2E8BD;
    }
    """,
    "wood": """
    :root {
      --cp-page:#F7F7F5; --cp-surface:#FFFFFF; --cp-soft:#F1EDE8;
      --cp-ink:#302C29; --cp-muted:#77716C; --cp-line:#E7E2DC;
      --cp-accent:#AB7C59; --cp-accent-hover:#8E6347; --cp-action:#6B5142;
      --cp-action-text:#FFFFFF; --cp-sidebar:#F0ECE7; --cp-logo:#DEC8B5;
      --cp-notice:#F9F5EF; --cp-notice-line:#E9DDD1;
    }
    """,
}

_BASE_CSS = """
.stApp { background:var(--cp-page); color:var(--cp-ink); }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { background:var(--cp-sidebar); }
.block-container { padding-top:1.15rem; padding-bottom:2rem; max-width:1700px; }
h1, h2, h3, h4 { color:var(--cp-ink) !important; letter-spacing:-0.035em; }
h1 { font-size:2rem !important; }
p, label { letter-spacing:-0.015em; }
.ev-header { display:flex; align-items:center; gap:13px; padding:3px 0 12px; }
.ev-logo { display:grid; place-items:center; position:relative; width:46px; height:46px; border-radius:15px; background:var(--cp-logo); color:var(--cp-ink); font-size:25px; box-shadow:0 5px 16px #65471524; overflow:hidden; }
.ev-brand { font-weight:850; font-size:22px; line-height:1.18; color:var(--cp-ink); letter-spacing:-.035em; }
.ev-brand small { display:block; font-size:11px; font-weight:650; color:var(--cp-muted); letter-spacing:.02em; margin-top:4px; }
.ev-banner { border:1px solid var(--cp-notice-line); background:var(--cp-notice); border-radius:13px; padding:11px 15px; color:var(--cp-ink); font-size:13px; margin-bottom:16px; }
.ev-section { font-size:16px; font-weight:800; color:var(--cp-ink); margin:4px 0 10px; }
.ev-small { color:var(--cp-muted); font-size:12px; }
.ev-empty { background:var(--cp-soft); color:var(--cp-ink); border:1px solid var(--cp-line); border-radius:13px; padding:13px 14px; font-size:13px; line-height:1.5; }
.ev-pill { display:inline-block; border-radius:999px; padding:5px 10px; font-size:12px; font-weight:750; margin:2px 0 7px; }
.ev-good { color:#3d5b36; background:#e8f1dd; }
.ev-delay { color:#745000; background:#fff0b0; }
.ev-off { color:#645a51; background:#eee9e0; }
.ev-candidate { color:#735a25; background:#fff9e8; border:1px dashed #bb9a4b; }
.ev-card-meta { font-size:12px; color:var(--cp-muted); margin-top:7px; line-height:1.5; }
.ev-card-detail { font-size:13px; color:var(--cp-ink); margin:4px 0; line-height:1.5; }
.ev-summary { font-size:14px; color:var(--cp-ink); font-weight:750; margin:8px 0; }
.ev-kpi { min-height:110px; background:var(--cp-surface); border:1px solid var(--cp-line); border-radius:16px; padding:16px; margin-bottom:8px; box-shadow:0 3px 14px #5a3c1810; }
.ev-kpi-label { color:var(--cp-muted); font-size:12px; font-weight:700; }
.ev-kpi-value { color:var(--cp-ink); font-size:26px; font-weight:800; margin-top:8px; }
.ev-kpi-highlight { background:var(--cp-soft); border-color:var(--cp-line); }
div[data-testid="stVerticalBlockBorderWrapper"] > div { border-color:var(--cp-line); border-radius:16px; background:var(--cp-surface); }
div.stButton > button { border-radius:11px; min-height:2.7rem; font-weight:700; transition:transform .16s ease, box-shadow .16s ease, background-color .16s ease; }
div.stButton > button:hover { transform:translateY(-1px); box-shadow:0 5px 12px #5a3c1820; }
div.stButton > button:focus-visible { outline:3px solid var(--cp-accent); outline-offset:2px; }
div.stButton > button[kind="primary"] { background:var(--cp-action); border-color:var(--cp-action); color:var(--cp-action-text); }
div.stButton > button[kind="primary"]:hover { background:var(--cp-accent-hover); border-color:var(--cp-accent-hover); color:var(--cp-ink); }
div.stButton > button[kind="secondary"] { background:var(--cp-surface); border:1px solid var(--cp-line); color:var(--cp-ink); }
div.stButton > button[kind="tertiary"] { background:transparent; color:var(--cp-ink); border:0; padding-left:0; box-shadow:none; }
[data-testid="stRadioGroup"][data-orientation="horizontal"] { gap:7px; flex-wrap:wrap; }
[data-testid="stRadioGroup"][data-orientation="horizontal"] > div { margin:0 !important; }
[data-testid="stRadioGroup"][data-orientation="horizontal"] [data-testid="stRadioOption"] { padding:7px 13px; border:1px solid var(--cp-line); border-radius:10px; background:var(--cp-surface); cursor:pointer; transition:background-color .16s ease, border-color .16s ease; }
[data-testid="stRadioGroup"][data-orientation="horizontal"] [data-testid="stRadioOption"]:hover { background:var(--cp-soft); }
[data-testid="stRadioGroup"][data-orientation="horizontal"] [data-testid="stRadioOption"][data-selected="true"] { background:var(--cp-accent); border-color:var(--cp-accent); }
[data-testid="stRadioGroup"][data-orientation="horizontal"] [data-testid="stRadioOption"] > div > div:first-child { display:none; }
[data-testid="stRadioGroup"][data-orientation="horizontal"] [data-testid="stRadioOption"] p { color:var(--cp-ink) !important; font-weight:650; }
[data-testid="stRadioOption"]:has(input:focus-visible) { outline:3px solid var(--cp-accent); outline-offset:2px; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] { padding:7px 11px; border-radius:10px; transition:background-color .16s ease; }
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] { background:var(--cp-surface); }
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child { display:none; }
div[data-testid="stChatMessage"] { border-radius:15px; }
:is(.st-key-user_logout, .st-key-dashboard_logout) div.stButton button {
  display:grid; place-items:center; width:46px !important; height:46px !important; min-height:46px !important;
  padding:0 !important; border-radius:50% !important; border:2px solid #AEB7C0 !important;
  background:#202832 !important; color:#F8FAFC !important;
  box-shadow:0 0 0 3px #E9EDF0, inset 0 0 0 1px #56616C !important;
}
:is(.st-key-user_logout, .st-key-dashboard_logout) div.stButton button p { font-size:24px !important; line-height:1 !important; font-weight:400 !important; }
:is(.st-key-user_logout, .st-key-dashboard_logout) div.stButton button:hover { background:#344150 !important; }
@media(max-width:768px) {
  .block-container { padding:1rem; }
  .ev-brand { font-size:19px; }
  [data-testid="stHorizontalBlock"] { flex-wrap:wrap; }
  [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { width:100% !important; min-width:0 !important; flex:1 1 100% !important; }
  [data-testid="stHorizontalBlock"]:has(.st-key-chat_panel) > [data-testid="stColumn"]:has(.st-key-chat_panel) { order:-1; }
}
@media(prefers-reduced-motion:reduce) { * { transition-duration:0.01ms !important; animation-duration:0.01ms !important; } }
"""


def apply_styles(theme: str = "honey") -> None:
    palette = _PALETTES.get(theme, _PALETTES["honey"])
    st.markdown("<style>" + palette + _BASE_CSS + "</style>", unsafe_allow_html=True)


def show_header(name: str = "ChargePin", subtitle: str = "서울 전기차 충전·주차 안내") -> None:
    st.markdown(
        '<div class="ev-header"><div class="ev-logo">'
        '<svg viewBox="0 0 24 24" width="29" height="29" fill="none" aria-hidden="true">'
        '<path d="M13.6 2.2 5.4 13h5.5L9.8 21.8 18.6 10h-5.4l.4-7.8Z" fill="currentColor" stroke="currentColor" stroke-width=".6" stroke-linejoin="round"/>'
        '</svg></div><div class="ev-brand">'
        + escape(name) + "<small>" + escape(subtitle) + "</small></div></div>",
        unsafe_allow_html=True,
        width="content",
    )


def show_preview_notice(admin: bool = False) -> None:
    message = (
        "운영 화면 미리보기 · 표시된 수치와 이력은 예시이며, 실제 인증과 운영 기능은 연결되지 않았어요."
        if admin else
        "화면 미리보기 · 장소와 상태는 예시 데이터이며, 실제 검색 결과가 아닙니다."
    )
    st.markdown('<div class="ev-banner">' + escape(message) + "</div>", unsafe_allow_html=True)


def render_status(card: dict[str, Any]) -> None:
    status, kind = card.get('status'), card.get('kind')
    if status == "AVAILABLE" and kind == "주차장":
        message, css = f"빈자리 {card.get('available_spaces')}면 (마지막 보고 기준)", "ev-good"
    elif status == "AVAILABLE":
        message, css = "충전기 상태 제공", "ev-good"
    elif status == "DELAYED":
        message, css = "정보 지연", "ev-delay"
    elif status == "CANDIDATE_ONLY":
        message, css = "장소 후보만", "ev-candidate"
    else:
        message, css = "확인 불가", "ev-off"
    st.markdown('<span class="ev-pill ' + css + '">' + escape(message) + "</span>", unsafe_allow_html=True)

    if status == "AVAILABLE" and kind == "주차장":
        st.markdown(
            '<div class="ev-card-detail">총 ' + escape(str(card.get('total_spaces')))
            + "면 · 현재 " + escape(str(card.get('current_vehicles'))) + "대</div>",
            unsafe_allow_html=True,
        )
    elif status == "AVAILABLE" and kind == "충전소":
        for name, value in card.get('chargers', []):
            st.markdown(
                '<div class="ev-card-detail">' + escape(str(name)) + " · " + escape(str(value)) + "</div>",
                unsafe_allow_html=True,
            )
    elif card.get('reason'):
        st.markdown('<div class="ev-card-detail">' + escape(str(card['reason'])) + "</div>", unsafe_allow_html=True)

    source = escape(str(card.get('source', "출처 확인 불가")))
    reported_at = card.get("reported_at")
    fetched_at = card.get("fetched_at")
    report_label = escape(str(reported_at)) + " 보고" if reported_at else "보고 시각 없음"
    fetch_label = escape(str(fetched_at)) + " 조회" if fetched_at else "조회 시각 없음"
    st.markdown('<div class="ev-card-meta">' + source + " · " + report_label + " · " + fetch_label + "</div>", unsafe_allow_html=True)


def show_metric(name: str, value: str, highlight: bool = False) -> None:
    style = "ev-kpi ev-kpi-highlight" if highlight else "ev-kpi"
    st.markdown(
        '<div class="' + style + '"><div class="ev-kpi-label">'
        + escape(name) + '</div><div class="ev-kpi-value">' + escape(value) + "</div></div>",
        unsafe_allow_html=True,
    )

