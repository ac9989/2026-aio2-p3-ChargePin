"""Shared preview entry screen for the ChargePin interfaces."""
from __future__ import annotations

import hmac
import os
from pathlib import Path

import streamlit as st

from components.styles import show_header

_ENTRY_STYLES = """
<style>
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display:none; }
[data-testid="stMainBlockContainer"] { max-width:1100px; padding-top:clamp(4rem, 12vh, 8rem); }
.entry-eyebrow { color:#9B6A10; font-size:12px; font-weight:850; letter-spacing:.13em; margin-bottom:14px; }
.entry-title { color:var(--cp-ink); font-size:clamp(30px, 4vw, 44px) !important; line-height:1.23; letter-spacing:-.055em; margin:0 0 18px; }
.entry-title span { color:#BD8613; }
.entry-copy { color:var(--cp-muted); font-size:15px; line-height:1.8; margin-bottom:22px; }
.st-key-entry_image img { border-radius:18px; box-shadow:0 12px 32px #72552a18; }
.st-key-entry_card [data-testid="stVerticalBlockBorderWrapper"] > div { padding:28px; border-radius:22px; box-shadow:0 14px 40px #604a2512; }
.entry-card-title { color:var(--cp-ink); font-size:22px; font-weight:800; letter-spacing:-.04em; margin:18px 0 6px; }
.entry-card-copy { color:var(--cp-muted); font-size:13px; line-height:1.6; margin-bottom:12px; }
@media(max-width:768px) {
  [data-testid="stMainBlockContainer"] { padding-top:3.5rem; }
  .entry-title { font-size:30px !important; }
  .st-key-entry_card [data-testid="stVerticalBlockBorderWrapper"] > div { padding:20px; }
}
</style>
"""


def clear_preview_session() -> None:
    st.session_state.clear()


def _check_entry_code() -> None:
    entered = str(st.session_state.get("entry_code", "")).strip().casefold().encode("utf-8")
    user_code = os.environ.get("CHARGEPIN_USER_CODE", "aio2boot").strip().casefold().encode("utf-8")
    admin_code = os.environ.get("CHARGEPIN_ADMIN_CODE", "aio2").strip().casefold().encode("utf-8")
    configuration_valid = bool(user_code and admin_code) and not hmac.compare_digest(user_code, admin_code)
    role = None
    if configuration_valid:
        if hmac.compare_digest(entered, admin_code):
            role = "admin"
        elif hmac.compare_digest(entered, user_code):
            role = "user"
    st.session_state.entry_role = role
    st.session_state.entry_granted = role is not None
    st.session_state.entry_error = role is None and configuration_valid
    st.session_state.entry_configuration_error = not configuration_valid
    st.session_state.entry_code = ""


def require_entry() -> bool:
    if st.session_state.get("entry_granted", False) and st.session_state.get("entry_role") in ("user", "admin"):
        return True

    st.markdown(_ENTRY_STYLES, unsafe_allow_html=True)
    intro, card = st.columns([1.1, 1], gap="large", vertical_alignment="center")
    with intro:
        st.markdown(
            '<div class="entry-eyebrow">CHARGEPIN · SEOUL</div>'
            '<h1 class="entry-title">충전할 곳,<br><span>가기 전에 확인해요.</span></h1>'
            '<div class="entry-copy">충전기 종류와 이용 조건, 별도의 주차 요금까지<br>'
            '직접 찾아보거나 차지핀에게 편하게 물어보세요.</div>',
            unsafe_allow_html=True,
        )
        image_path = Path(__file__).resolve().parents[1] / "static" / "entry-ev.png"
        with st.container(key="entry_image"):
            st.image(str(image_path), caption=None, width="stretch", alt="맑은 하늘 아래 주차장에서 충전 중인 전기차")
    with card:
        with st.container(border=True, key="entry_card"):
            show_header()
            st.markdown('<div class="entry-card-title">시작하기</div>', unsafe_allow_html=True)
            st.markdown('<div class="entry-card-copy">접속 코드를 입력하고 차지핀을 시작해 주세요.</div>', unsafe_allow_html=True)
            with st.form("entry_form", border=False):
                st.text_input("접속 코드", type="password", placeholder="접속 코드 입력", key="entry_code", max_chars=128)
                st.form_submit_button("입장하기", type="primary", width="stretch", on_click=_check_entry_code)
            if st.session_state.get("entry_configuration_error", False):
                st.error("접속 코드 설정을 확인해 주세요.")
            elif st.session_state.get("entry_error", False):
                st.error("접속 코드가 맞지 않아요. 다시 확인해 주세요.")
            st.caption("시연용 접속 코드로 사용자와 관리자를 구분합니다.")
    return False