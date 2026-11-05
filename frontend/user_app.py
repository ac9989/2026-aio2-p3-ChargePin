"""User interface for Seoul EV charging and parking."""
from __future__ import annotations

from copy import deepcopy
from html import escape
from typing import Any

import streamlit as st

from components.styles import apply_styles, show_header, show_preview_notice, render_status
from components.entry import clear_preview_session, require_entry
from components.map_component import show_map
from services.preview import (
    ACCESS_OPTIONS, CITY_HALL_CENTER, DEFAULT_CENTER, LIMIT_OPTIONS, OCCUPANCY_OPTIONS,
    PARKING_FEE_OPTIONS, SEOUL_DISTRICTS, SITE_TYPE_OPTIONS, PreviewProvider,
    SearchCriteria, marker_information, parse_preview_query, site_information,
)

_USER_STYLES = """
<style>
.st-key-search_panel { background:var(--cp-surface); border:1px solid #D7E0E8 !important; border-radius:18px !important; padding:22px !important; gap:12px !important; box-shadow:0 10px 30px #2334480a; }
.search-kicker { color:#A27A18; font-size:11px; font-weight:800; letter-spacing:.04em; margin-bottom:6px; }
.search-title { color:var(--cp-ink); font-size:20px; font-weight:800; letter-spacing:-.04em; line-height:1.3; }
.search-copy { color:var(--cp-muted); font-size:12px; line-height:1.5; margin:5px 0 8px; }
.st-key-search_panel [data-testid="stWidgetLabel"] p { color:var(--cp-ink); font-size:13px; font-weight:700; }
.st-key-search_panel .st-key-filter_region [role="group"] { background:#FFF; border:1px solid #C8D3DD; border-radius:10px; transition:border-color .16s ease, box-shadow .16s ease; }
.st-key-search_panel .st-key-filter_region [role="group"]:focus-within { border-color:#BE9226; box-shadow:0 0 0 3px #F5CB4638; }
.st-key-search_panel > .st-key-filter_region + [data-testid="stElementContainer"] { margin-top:-6px; }
.st-key-search_panel > .st-key-run_search { margin-top:12px; }
.st-key-search_panel > .st-key-run_search + [data-testid="stElementContainer"] { margin-top:-4px; }
.st-key-search_panel [data-testid="stRadioGroup"][data-orientation="horizontal"] { width:100%; display:flex; flex-wrap:nowrap; gap:6px; padding:0; background:transparent; }
.st-key-search_panel [data-testid="stRadioGroup"][data-orientation="horizontal"] > div { flex:1 1 0; min-width:0; }
.st-key-search_panel [data-testid="stRadioGroup"][data-orientation="horizontal"] [data-testid="stRadioOption"] { display:flex; justify-content:center; width:100%; min-height:40px; padding:8px 4px; border:1px solid #CBD5DF; border-radius:10px; background:#FFF; }
.st-key-search_panel [data-testid="stRadioGroup"][data-orientation="horizontal"] [data-testid="stRadioOption"]:hover { border-color:#B99A4D; background:#FFFCF2; }
.st-key-search_panel [data-testid="stRadioGroup"][data-orientation="horizontal"] [data-testid="stRadioOption"][data-selected="true"] { background:#FFD044; border-color:#D2A122; box-shadow:0 2px 5px #64481214; }
.st-key-search_panel [data-testid="stRadioGroup"][data-orientation="horizontal"] [data-testid="stRadioOption"] p { color:#26313C !important; font-size:12px; font-weight:700; text-align:center; }
.st-key-run_search div.stButton > button { background:#F5CB46 !important; border:1px solid #D3A322 !important; color:#202A35 !important; border-radius:10px; min-height:46px; }
.st-key-run_search div.stButton > button:disabled { background:#EEF1F4 !important; border-color:#D6DEE5 !important; color:#8A97A3 !important; box-shadow:none !important; cursor:not-allowed; }
.st-key-run_search div.stButton > button:disabled p { color:#8A97A3 !important; }
.st-key-extra_filters button { width:100%; min-height:40px; border:1px solid #CBD5DF; border-radius:10px; background:#FFF; color:#26313C; }
.st-key-extra_filters button:hover { border-color:#B99A4D; background:#FFFCF2; }
[class*="st-key-extra_"] [data-testid="stRadioGroup"] { gap:5px; flex-wrap:wrap; }
[class*="st-key-extra_"] [data-testid="stRadioGroup"] [data-testid="stRadioOption"] { padding:6px 9px; border:1px solid #D6DFE7; border-radius:8px; background:#FFF; }
[class*="st-key-extra_"] [data-testid="stRadioGroup"] [data-testid="stRadioOption"][data-selected="true"] { background:#FFF2BD; border-color:#D1A534; }
[class*="st-key-extra_"] [data-testid="stRadioOption"] p { font-size:12px; color:#26313C; }
.st-key-brand_and_preview { gap:12px !important; }
[class*="st-key-preview_states_"] button { min-height:34px; padding:5px 10px; border:1px solid #C8D3DD; border-radius:9px; background:#FFF; color:#3C4A58; font-size:12px; }
[class*="st-key-preview_states_"] button:hover { border-color:#A98A42; background:#FFFCF2; }
.st-key-preview_state [data-testid="stRadioGroup"] { width:100%; gap:3px; }
.st-key-preview_state [data-testid="stRadioGroup"] > div { width:100%; }
.st-key-preview_state [data-testid="stRadioOption"] { width:100%; min-height:36px; padding:7px 9px; border:1px solid transparent; border-radius:9px; cursor:pointer; }
.st-key-preview_state [data-testid="stRadioOption"]:hover { background:#F4F6F8; }
.st-key-preview_state [data-testid="stRadioOption"][data-selected="true"] { background:#FFF8DF; border-color:#E8D698; }
.st-key-preview_state [data-testid="stRadioOption"] p { color:#26313C; font-size:13px; }
.st-key-user_header_actions div.stButton > button { min-height:2.45rem; padding:.35rem .9rem; border-radius:11px; font-size:13px; }
.st-key-open_dashboard div.stButton > button { background:transparent; }
.map-heading { display:flex; align-items:center; gap:12px; margin:0 1px 10px; }
.map-heading b { color:var(--cp-ink); font-size:17px; letter-spacing:-.03em; }
.search-summary { background:#F6F8FA; border:1px solid #E9EDF1; border-radius:11px; padding:11px 12px; color:var(--cp-ink); font-size:12px; font-weight:700; line-height:1.5; }
[class*="st-key-place_card_"] { border:1px solid #E5EAF0 !important; border-radius:13px !important; padding:13px !important; background:#FFFFFF; }
.site-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:7px; margin-top:10px; padding:10px; background:#F6F8FA; border-radius:10px; }
.site-grid small { display:block; color:#788492; font-size:10px; margin-bottom:4px; }
.site-grid strong { color:#26313C; font-size:11px; line-height:1.4; word-break:keep-all; }
.site-note { color:#6D7986; font-size:11px; margin-top:7px; line-height:1.45; }
.ev-banner { background:#FFFBEC; border-color:#F1E8C7; }
</style>
"""

_GLOBAL_PREVIEW_MESSAGES = {
    "요청 제한": ("warning", "요청이 많아 잠시 멈췄어요. 조금 뒤에 다시 시도해 주세요."),
    "인증 만료": ("info", "로그인이 만료됐어요. 다시 로그인한 뒤 이용해 주세요."),
    "권한 없음": ("error", "이 기능을 이용할 수 있는 권한이 없어요."),
}


def preview_requests_blocked() -> bool:
    return st.session_state.get("preview_state") in _GLOBAL_PREVIEW_MESSAGES


def sync_preview_scope() -> None:
    st.session_state.preview_menu_revision = st.session_state.get("preview_menu_revision", 0) + 1
    state = st.session_state.get("preview_state")
    if state == "AI 챗 연결 실패":
        st.session_state.search_mode = "AI 챗"
    elif state in ("결과 없음", "일부 정보 지연"):
        st.session_state.search_mode = "탐색"


def show_global_preview() -> None:
    state = st.session_state.get("preview_state")
    if state in _GLOBAL_PREVIEW_MESSAGES:
        level, message = _GLOBAL_PREVIEW_MESSAGES[state]
        getattr(st, level)("[시연] " + message)


def show_search_preview() -> bool:
    state = st.session_state.get("preview_state")
    if state == "결과 없음":
        st.info("[시연] 이 조건에 맞는 충전 장소가 없어요. 지역이나 반경을 바꿔 보세요.")
        return True
    if state == "일부 정보 지연":
        st.warning("[시연] 일부 시설의 정보가 지연되고 있어요. 나머지 결과는 확인할 수 있어요.")
    return False


def initialize_state() -> None:
    defaults = {
        "map_center": DEFAULT_CENTER, "result_list": [], "search_complete": False,
        "last_criteria": None, "selected_facility": None, "filters_open": True,
        "chat_messages": [{
            "role": "assistant",
            "content": "안녕하세요, 차지핀이에요. 서울이나 강남처럼 지역을 말씀해 주시면 주변 충전 장소부터 찾아볼게요.",
        }],
    }
    for name, value in defaults.items():
        if name not in st.session_state:
            st.session_state[name] = deepcopy(value)


def run_preview_search(criteria: SearchCriteria) -> None:
    st.session_state.result_list = PreviewProvider().search(criteria)
    st.session_state.search_complete = True
    st.session_state.last_criteria = criteria
    st.session_state.map_center = (criteria.latitude, criteria.longitude)
    st.session_state.selected_facility = None
    st.session_state.filters_open = False


def show_cards() -> None:
    if not st.session_state.search_complete:
        if preview_requests_blocked():
            st.caption("시연을 해제하면 다시 검색할 수 있어요.")
        else:
            st.caption("조건을 고르고 검색해 주세요.")
        return
    results = st.session_state.result_list
    st.markdown('<div class="ev-summary">예시 결과 ' + str(len(results)) + '곳</div>', unsafe_allow_html=True)
    st.caption("주차 요금은 충전 요금과 별도예요.")
    if not results:
        st.info("이 조건에 맞는 예시 충전 장소가 없어요. 지역이나 반경을 바꿔 보세요.")
        return
    if any(card.get("status") == "DELAYED" for card in results):
        st.warning("일부 예시 시설의 상태가 지연되어 있어요.")
    for card in results:
        with st.container(border=True, key="place_card_" + card["id"]):
            if st.button(card["name"], key="card_" + card["id"], type="tertiary", width="stretch", help="지도에서 이 장소를 강조합니다."):
                st.session_state.selected_facility = card["id"]
                st.rerun()
            distance = card.get("distance_km")
            distance_text = f"직선 {distance:.1f} km · " if isinstance(distance, (int, float)) else ""
            st.caption(distance_text + str(card.get("address") or "주소 확인 필요"))
            if card["id"] == st.session_state.selected_facility:
                st.caption("지도에서 선택한 장소")
            render_status(card)
            info = site_information(card)
            detail = marker_information(card)
            st.markdown(
                '<div class="site-grid"><div><small>장소 유형</small><strong>' + escape(info["site_type"])
                + '</strong></div><div><small>주차 요금</small><strong>' + escape(info["parking_fee"])
                + '</strong></div><div><small>외부인 이용</small><strong>' + escape(info["access"])
                + '</strong></div></div>'
                + ('<div class="site-note">' + escape(info["access_detail"]) + '</div>' if info["access_detail"] else '')
                + '<div class="site-note">이용 제한시간 · ' + escape(detail["usage_limit"]) + '</div>',
                unsafe_allow_html=True,
            )


def chat_result_message(criteria: SearchCriteria, center_label: str, results: list[dict[str, Any]]) -> str:
    speed = "급속·완속" if criteria.connector_type == "전체" else criteria.connector_type
    heading = f"**{center_label} 기준 {criteria.radius} km · {speed} 예시 결과**"
    if not results:
        return heading + "\n\n조건에 맞는 예시 충전 장소가 없어요. 반경을 넓히거나 다른 조건을 말씀해 주세요."
    lines = [heading]
    for card in results[:3]:
        info = marker_information(card)
        charger = info["charger_type"] if info["charger_type"] != "확인 필요" else "충전기 종류 확인 필요"
        detail = f" ({info['access_detail']})" if info["access_detail"] else ""
        lines.append(f"- **{card['name']}** · {charger} · 주차 {info['parking_fee']} · 외부인 이용 {info['access']}{detail}")
    if len(results) > 3:
        lines.append(f"- 지도에서 나머지 {len(results) - 3}곳도 확인할 수 있어요.")
    if criteria.connector_type == "급속":
        lines.append("완속 충전소도 함께 볼까요? 다른 위치를 원하시면 지역을 알려 주세요.")
    else:
        lines.append("다른 지역이나 주차·이용 조건을 말씀해 주세요.")
    return "\n\n".join(lines)


def show_chat() -> None:
    st.markdown('<div class="ev-section">차지핀에게 물어보기</div>', unsafe_allow_html=True)
    st.caption("예시 대화 · 실제 AI와 외부 검색은 연결되지 않았어요.")
    chat_failed = st.session_state.get("preview_state") == "AI 챗 연결 실패"
    if chat_failed:
        st.warning("[시연] AI 챗에 연결할 수 없어 입력이 잠겼어요. 잠시 후 다시 시도해 주세요.")
    with st.container(height=310, border=True, key="chat_messages", autoscroll=True):
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"], avatar="⚡" if message["role"] == "assistant" else "👤"):
                st.write(message["content"])
    chat_blocked = chat_failed or preview_requests_blocked()
    placeholder = "시연 중에는 채팅 입력이 잠겨 있어요." if chat_blocked else "예: 강남역 주차 무료 급속 충전소"
    query = st.chat_input(placeholder, disabled=chat_blocked)
    if query:
        st.session_state.chat_messages.append({"role": "user", "content": query})
        interpretation = parse_preview_query(query, st.session_state.map_center, st.session_state.last_criteria)
        if "criteria" in interpretation:
            criteria = interpretation["criteria"]
            run_preview_search(criteria)
            reply = chat_result_message(criteria, interpretation["center_label"], st.session_state.result_list)
        else:
            reply = interpretation["message"]
        st.session_state.chat_messages.append({"role": "assistant", "content": reply})
        st.rerun()


def reset_extra_filters() -> None:
    for key in ("extra_site", "extra_fee", "extra_access", "extra_occupancy", "extra_limit"):
        st.session_state[key] = "전체"


def update_region_center() -> None:
    region = st.session_state.get("filter_region")
    centers = {"서울 전체": CITY_HALL_CENTER, "중구": CITY_HALL_CENTER, "강남구": DEFAULT_CENTER}
    if region in centers:
        st.session_state.map_center = centers[region]
    st.session_state.result_list = []
    st.session_state.search_complete = False
    st.session_state.last_criteria = None
    st.session_state.selected_facility = None


def show_extra_filters(criteria: SearchCriteria | None) -> dict[str, str]:
    specs = (
        ("장소 유형", SITE_TYPE_OPTIONS, "extra_site", criteria.site_type if criteria else "전체"),
        ("주차 요금", PARKING_FEE_OPTIONS, "extra_fee", criteria.parking_fee if criteria else "전체"),
        ("외부인 이용", ACCESS_OPTIONS, "extra_access", criteria.access if criteria else "전체"),
        ("주차 현황", OCCUPANCY_OPTIONS, "extra_occupancy", criteria.parking_occupancy if criteria else "전체"),
        ("충전기 이용 제한시간", LIMIT_OPTIONS, "extra_limit", criteria.usage_limit if criteria else "전체"),
    )
    selected = {}
    with st.popover("추가 조건", key="extra_filters", width="stretch"):
        st.caption("확인된 정보만 조건에 맞춰 보여줘요. 주차 요금은 충전 요금과 별도예요.")
        for label, options, key, current in specs:
            selected[key] = st.radio(
                label, options, index=options.index(current) if current in options else 0,
                key=key, horizontal=True, width="stretch",
            )
        st.caption("외부인 이용 기준이에요. 주차 현황과 충전기 사용 상태는 서로 달라요.")
        st.button("추가 조건 초기화", key="reset_extra", on_click=reset_extra_filters)
    active = [value for value in selected.values() if value != "전체"]
    if active:
        st.caption("추가 조건 · " + " · ".join(active))
    return selected


def show_direct_search() -> int:
    criteria = st.session_state.last_criteria
    radius = criteria.radius if criteria is not None else 3
    if st.session_state.search_complete and not st.session_state.filters_open:
        parts = [criteria.region, criteria.connector_type, f"{criteria.radius} km"]
        parts.extend(value for value in (
            criteria.site_type, criteria.parking_fee, criteria.access,
            criteria.parking_occupancy, criteria.usage_limit,
        ) if value != "전체")
        st.markdown('<div class="search-summary">' + escape(" · ".join(parts)) + '</div>', unsafe_allow_html=True)
        if st.button("조건 변경", key="change_filters", width="stretch"):
            st.session_state.filters_open = True
            st.rerun()
        if show_search_preview():
            return radius
        if st.session_state.result_list:
            with st.container(height=420, border=False, key="search_results"):
                show_cards()
        else:
            show_cards()
        return radius

    region_index = SEOUL_DISTRICTS.index(criteria.region) if criteria is not None else 0
    region = st.selectbox("지역", SEOUL_DISTRICTS, index=region_index, key="filter_region", on_change=update_region_center)
    latitude, longitude = st.session_state.map_center
    if region not in ("서울 전체", "중구", "강남구"):
        st.caption("이 지역은 지도에서 검색 중심을 선택해 주세요.")
    else:
        st.caption("지도에서 검색 중심을 선택할 수 있어요.")
    connectors = ["전체", "급속", "완속"]
    connector_index = connectors.index(criteria.connector_type) if criteria is not None else 0
    connector_type = st.radio("충전기 타입", connectors, index=connector_index, horizontal=True, key="filter_connector", width="stretch")
    radii = [1, 3, 5]
    radius_index = radii.index(radius)
    radius = st.radio("검색 반경", radii, index=radius_index, horizontal=True, format_func=lambda value: f"{value} km", key="filter_radius", width="stretch")
    extra = show_extra_filters(criteria)
    if st.button("검색", type="primary", width="stretch", key="run_search", disabled=preview_requests_blocked()):
        try:
            run_preview_search(SearchCriteria(
                region, latitude, longitude, connector_type, radius,
                extra["extra_site"], extra["extra_fee"], extra["extra_access"],
                extra["extra_occupancy"], extra["extra_limit"],
            ))
            st.rerun()
        except ValueError as error:
            st.error(str(error))
    if st.session_state.search_complete:
        if st.button("결과로 돌아가기", width="stretch", key="close_filters"):
            st.session_state.filters_open = False
            st.rerun()
        show_search_preview()
    elif not show_search_preview():
        show_cards()
    return radius


def show_state_preview() -> None:
    with st.popover("상태 시연", key=f"preview_states_{st.session_state.get('preview_menu_revision', 0)}"):
        st.caption("상황을 선택하면 바로 화면에 적용돼요.")
        st.radio(
            "시연할 상황",
            ["시연 해제", "결과 없음", "일부 정보 지연", "요청 제한", "인증 만료", "권한 없음", "AI 챗 연결 실패"],
            key="preview_state", on_change=sync_preview_scope, width="stretch",
        )


def main() -> None:
    initialize_state()
    st.markdown(_USER_STYLES, unsafe_allow_html=True)
    title_column, tools_column = st.columns([6, 4], vertical_alignment="center")
    with title_column:
        with st.container(key="brand_and_preview", horizontal=True, vertical_alignment="center", gap="small", wrap=True):
            show_header()
            show_state_preview()
    with tools_column:
        with st.container(key="user_header_actions", horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small", wrap=True):
            if st.session_state.get("entry_role") == "admin":
                if st.button("관리자 대시보드", width="content", key="open_dashboard"):
                    st.session_state.active_view = "dashboard"
                    st.rerun()
            st.button("⏻", width=46, key="user_logout", help="현재 접속을 마칩니다.", on_click=clear_preview_session)
    show_preview_notice()
    show_global_preview()

    columns = st.columns([3.4, 8], gap="medium")
    with columns[0]:
        with st.container(border=True, key="search_panel"):
            st.markdown(
                '<div class="search-kicker">CHARGEPIN</div><div class="search-title">충전 장소 찾기</div>'
                '<div class="search-copy">직접 고르거나 대화로 찾아보세요.</div>',
                unsafe_allow_html=True,
            )
            mode = st.radio("검색 방식", ["탐색", "AI 챗"], horizontal=True, label_visibility="collapsed", key="search_mode", width="stretch")
            if mode == "AI 챗":
                show_chat()
                criteria = st.session_state.last_criteria
                radius = criteria.radius if criteria is not None else 3
            else:
                radius = show_direct_search()

    with columns[1]:
        st.markdown('<div class="map-heading"><b>주변 지도</b></div>', unsafe_allow_html=True)
        criteria = st.session_state.last_criteria
        display_radius = criteria.radius if criteria is not None else radius
        empty_preview = st.session_state.get("preview_state") == "결과 없음"
        visible_results = [] if empty_preview else st.session_state.result_list
        selected_facility = None if empty_preview else st.session_state.selected_facility
        event = show_map(st.session_state.map_center, display_radius, visible_results, selected_facility)
        st.caption("지도와 장소 후보는 실제 상태를 보장하지 않습니다. 현재 시설 정보는 예시입니다.")
        if event.get("marker_click"):
            st.session_state.selected_facility = (
                None if st.session_state.selected_facility == event["marker_click"] else event["marker_click"]
            )
            st.rerun()
        if event.get("map_click"):
            point = event["map_click"]
            try:
                new_center = (float(point["lat"]), float(point["lng"]))
                SearchCriteria(latitude=new_center[0], longitude=new_center[1]).confirm()
                st.session_state.map_center = new_center
                st.session_state.result_list = []
                st.session_state.search_complete = False
                st.session_state.last_criteria = None
                st.session_state.filters_open = True
                st.rerun()
            except (KeyError, TypeError, ValueError):
                st.error("서울 주변의 검색 중심을 선택해 주세요.")


def launch() -> None:
    is_dashboard = (
        st.session_state.get("entry_granted", False)
        and st.session_state.get("entry_role") == "admin"
        and st.session_state.get("active_view", "user") == "dashboard"
    )
    apply_styles("wood" if is_dashboard else "honey")
    if not require_entry():
        return
    if st.session_state.get("active_view", "user") == "dashboard":
        if st.session_state.get("entry_role") != "admin":
            st.error("관리자 권한이 필요한 화면이에요.")
            if st.button("사용자 화면으로 돌아가기"):
                st.session_state.active_view = "user"
                st.rerun()
            return
        from dashboard.app import render_dashboard
        render_dashboard()
    else:
        main()
