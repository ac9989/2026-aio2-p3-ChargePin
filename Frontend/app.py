"""ChargePin 1.0 Streamlit interface connected to the preview multi-agent backend."""
from __future__ import annotations

from html import escape
import json
import os
from typing import Any

import streamlit as st

from api_client import ApiError, ChargePinApi


st.set_page_config(page_title="ChargePin", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

API = ChargePinApi()
CONNECTOR_CODES = {"급속": "FAST", "완속": "SLOW"}
ROLE_LABELS = {"GUEST": "손님", "JUNIOR_ADMIN": "하급 관리자", "SENIOR_ADMIN": "상급 관리자"}

STYLES = """
<style>
:root { --cp-ink:#26313C; --cp-muted:#71808D; --cp-line:#D8E1E8; --cp-soft:#F5F8FA; --cp-surface:#FFF; --cp-gold:#F5CB46; --cp-gold-deep:#A27A18; --cp-alert:#B85D4A; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stAppViewContainer"] { background:linear-gradient(135deg,#FBFCFD 0%,#FFFDF7 100%); }
[data-testid="stMainBlockContainer"] { max-width:1440px; padding-top:1.7rem; }
.brand-row { display:flex; align-items:center; gap:10px; margin:0 0 4px; }
.brand-bolt { display:grid; place-items:center; width:32px; height:32px; border-radius:11px; background:var(--cp-gold); color:#333; font-size:17px; }
.brand-name { color:var(--cp-ink); font-size:21px; font-weight:850; letter-spacing:-.05em; }
.brand-sub { color:var(--cp-muted); font-size:12px; margin-top:2px; }
.shell-card { background:var(--cp-surface); border:1px solid var(--cp-line); border-radius:19px; padding:20px; box-shadow:0 10px 30px #2030400d; }
.search-kicker { color:var(--cp-gold-deep); font-size:11px; font-weight:850; letter-spacing:.12em; }
.search-title { color:var(--cp-ink); font-size:21px; font-weight:850; letter-spacing:-.045em; margin:6px 0 3px; }
.search-copy { color:var(--cp-muted); font-size:12px; line-height:1.55; margin-bottom:15px; }
.summary { padding:10px 12px; border-radius:11px; background:#FFF9E9; border:1px solid #F0E2B7; color:#5C4B26; font-size:12px; font-weight:700; line-height:1.5; margin:9px 0; }
.map-shell { position:relative; height:525px; overflow:hidden; border:1px solid #DCE8E5; border-radius:21px; background:#F2F7F2; box-shadow:0 10px 28px #536d6712; }
.map-grid { position:absolute; inset:0; background:linear-gradient(112deg,transparent 37%,#DCEEF2 37%,#DCEEF2 47%,transparent 47%),linear-gradient(0deg,transparent 39%,#FFF 39%,#FFF 40%,transparent 40%),linear-gradient(90deg,transparent 61%,#FFF 61%,#FFF 62%,transparent 62%),#F3F7F3; }
.map-label { position:absolute; top:14px; left:14px; z-index:5; max-width:78%; padding:8px 11px; border-radius:9px; background:#FFF; box-shadow:0 2px 10px #1232; color:#51412B; font-size:12px; }
.radius-ring { position:absolute; width:45%; aspect-ratio:1; left:27.5%; top:28%; border:2px dashed #C3922E; background:#F6D66F24; border-radius:50%; }
.center-dot { position:absolute; left:50%; top:50%; width:14px; height:14px; transform:translate(-50%,-50%); border:2px solid #FFF; border-radius:5px; background:#3A2D1B; }
.map-marker { position:absolute; z-index:3; transform:translate(-50%,-50%); }
.map-marker:hover, .map-marker:focus-within { z-index:10; }
.map-pin { width:37px; height:37px; border:2px solid #FFF; border-radius:50%; background:#40331D; box-shadow:0 2px 6px #0003; color:#FFF; cursor:pointer; font-weight:800; }
.map-pop { visibility:hidden; opacity:0; position:absolute; left:50%; bottom:calc(100% + 9px); width:240px; transform:translateX(-50%); padding:13px; border:1px solid #DEE5EA; border-radius:13px; background:#FFF; box-shadow:0 10px 28px #2433422B; color:var(--cp-ink); transition:.14s; }
.map-marker:hover .map-pop, .map-marker:focus-within .map-pop, .map-marker.open .map-pop { visibility:visible; opacity:1; }
.map-pop-title { font-size:13px; font-weight:800; margin-bottom:8px; }.map-pop-row { display:flex; justify-content:space-between; gap:8px; padding:3px 0; font-size:11px; }.map-pop-row span{color:#778490}.map-pop-row b{text-align:right}.map-pop-note{margin-top:7px;padding-top:7px;border-top:1px solid #EDF0F2;color:#8A959F;font-size:10px;line-height:1.4}
.map-legend { position:absolute; left:14px; bottom:14px; z-index:5; padding:9px 11px; border-radius:9px; background:#FFF; color:#5A472D; font-size:12px; box-shadow:0 2px 10px #1232; }
.station-card { border:1px solid #E5EAF0; border-radius:14px; padding:14px; background:#FFF; margin:9px 0; }.station-name{color:var(--cp-ink);font-size:14px;font-weight:800}.station-address{color:var(--cp-muted);font-size:11px;margin:4px 0 9px}.station-meta{display:flex;gap:7px;flex-wrap:wrap}.chip{display:inline-block;border-radius:999px;padding:4px 8px;background:#F4F7F9;color:#4A5968;font-size:10px;font-weight:750}.chip.ok{background:#E9F3E7;color:#386443}.chip.warn{background:#FFF3D6;color:#8A5E12}.status-line{margin-top:9px;color:#34424E;font-size:12px;font-weight:750}
.dashboard-hero { padding:19px; margin:12px 0 16px; border-radius:17px; background:#FFF9E9; border:1px solid #F0E2B7; }.metric-label{color:var(--cp-muted);font-size:11px;font-weight:750}.metric-value{color:var(--cp-ink);font-size:24px;font-weight:850;letter-spacing:-.05em}.detail-row{display:flex;justify-content:space-between;padding:9px 0;border-bottom:1px solid #EEF1F3;font-size:12px}.detail-row:last-child{border-bottom:0}
div.stButton > button { border-radius:11px; font-weight:750; } div.stButton > button[kind="primary"] { background:var(--cp-gold); border-color:#D3A322; color:#202A35; }
</style>
"""

MAP_CSS = """
<style>
body{margin:0;font-family:Arial,sans-serif}.map-shell{position:relative;height:525px;overflow:hidden;border:1px solid #DCE8E5;border-radius:21px;background:#F2F7F2}.map-grid{position:absolute;inset:0;background:linear-gradient(112deg,transparent 37%,#DCEEF2 37%,#DCEEF2 47%,transparent 47%),linear-gradient(0deg,transparent 39%,#FFF 39%,#FFF 40%,transparent 40%),linear-gradient(90deg,transparent 61%,#FFF 61%,#FFF 62%,transparent 62%),#F3F7F3}.map-label{position:absolute;top:14px;left:14px;z-index:5;max-width:78%;padding:8px 11px;border-radius:9px;background:#FFF;box-shadow:0 2px 10px #1232;color:#51412B;font-size:12px}.radius-ring{position:absolute;width:45%;aspect-ratio:1;left:27.5%;top:28%;border:2px dashed #C3922E;background:#F6D66F24;border-radius:50%}.center-dot{position:absolute;left:50%;top:50%;width:14px;height:14px;transform:translate(-50%,-50%);border:2px solid #FFF;border-radius:5px;background:#3A2D1B}.map-marker{position:absolute;z-index:3;transform:translate(-50%,-50%)}.map-marker:hover,.map-marker:focus-within{z-index:10}.map-pin{width:37px;height:37px;border:2px solid #FFF;border-radius:50%;background:#40331D;box-shadow:0 2px 6px #0003;color:#FFF;cursor:pointer;font-weight:800}.map-pop{visibility:hidden;opacity:0;position:absolute;left:50%;bottom:calc(100% + 9px);width:240px;transform:translateX(-50%);padding:13px;border:1px solid #DEE5EA;border-radius:13px;background:#FFF;box-shadow:0 10px 28px #2433422B;color:#26313C;transition:.14s}.map-marker:hover .map-pop,.map-marker:focus-within .map-pop,.map-marker.open .map-pop{visibility:visible;opacity:1}.map-pop-title{font-size:13px;font-weight:800;margin-bottom:8px}.map-pop-row{display:flex;justify-content:space-between;gap:8px;padding:3px 0;font-size:11px}.map-pop-row span{color:#778490}.map-pop-row b{text-align:right}.map-pop-note{margin-top:7px;padding-top:7px;border-top:1px solid #EDF0F2;color:#8A959F;font-size:10px;line-height:1.4}.map-legend{position:absolute;left:14px;bottom:14px;z-index:5;padding:9px 11px;border-radius:9px;background:#FFF;color:#5A472D;font-size:12px;box-shadow:0 2px 10px #1232}
.map-hover{visibility:hidden;opacity:0;position:absolute;left:50%;bottom:calc(100% + 9px);width:170px;transform:translateX(-50%);padding:9px 10px;border:1px solid #DEE5EA;border-radius:10px;background:#FFF;box-shadow:0 7px 20px #24334222;color:#26313C;font-size:11px}.map-hover b{display:block;font-size:12px;margin-bottom:4px}.map-hover span{color:#526270;font-weight:750}.map-marker:hover .map-hover,.map-marker:focus-within .map-hover{visibility:visible;opacity:1}.map-marker:hover .map-pop,.map-marker:focus-within .map-pop{visibility:hidden;opacity:0}.map-marker.open .map-pop{visibility:visible;opacity:1}.map-marker.open .map-hover{visibility:hidden;opacity:0}
</style>
"""


def init_state() -> None:
    defaults: dict[str, Any] = {
        "role": None, "auth_token": None, "view": "search", "mode": "탐색", "results": [], "request": None,
        "chat": [{"role": "assistant", "content": "안녕하세요, 차지핀이에요. 서울의 충전할 장소를 말씀해 주세요."}],
        "pending_plan": None, "notice": None, "booted": False, "place_query": "",
        "place_suggestions": [], "suggestion_query": "", "suggestion_error": None, "selected_place": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def set_search_response(payload: dict[str, Any]) -> None:
    st.session_state.results = payload.get("results", [])
    st.session_state.request = payload.get("applied_request")
    st.session_state.pending_plan = None
    findings = payload.get("critic_findings", [])
    st.session_state.notice = " · ".join(str(item) for item in findings) if findings else None


def access_token() -> str:
    return str(st.session_state.auth_token or "")


def load_default_once() -> None:
    if st.session_state.booted or not access_token():
        return
    st.session_state.booted = True
    try:
        set_search_response(API.default_search(access_token()))
    except ApiError as error:
        st.session_state.notice = error.message


def role_dialog(title: str, body: str) -> None:
    @st.dialog(title)
    def _dialog() -> None:
        st.write(body)
        st.button("확인", use_container_width=True)
    _dialog()


def render_login() -> None:
    _, center, _ = st.columns([2, 3, 2])
    with center:
        st.markdown('<div class="brand-row"><div class="brand-bolt">⚡</div><div><div class="brand-name">ChargePin</div><div class="brand-sub">서울 전기차 충전 자리 안내</div></div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("login-form", clear_on_submit=True):
            st.markdown("### 서비스 비밀번호 입력")
            st.caption("권한에 맞는 서비스 키를 입력하면 해당 역할로 접속합니다.")
            service_key = st.text_input("서비스 비밀번호", type="password", placeholder="서비스 키 입력", label_visibility="collapsed")
            submitted = st.form_submit_button("접속하기", type="primary", use_container_width=True)
        if submitted:
            try:
                session = API.login(service_key)
                st.session_state.auth_token = session["access_token"]
                st.session_state.role = ROLE_LABELS.get(session["role"], "손님")
                st.session_state.booted = False
                st.session_state.notice = None
                st.rerun()
            except ApiError as error:
                st.error(error.message)


def logout() -> None:
    st.session_state.auth_token = None
    st.session_state.role = None
    st.session_state.view = "search"
    st.session_state.results = []
    st.session_state.request = None
    st.session_state.pending_plan = None
    st.session_state.notice = None
    st.session_state.booted = False
    st.rerun()


def availability_label(station: dict[str, Any]) -> str:
    return station.get("availability", {}).get("label", "충전 상태 확인 불가")


def map_html(results: list[dict[str, Any]], request: dict[str, Any] | None) -> str:
    positions = ((34, 37), (65, 34), (31, 62), (68, 61), (52, 46))
    markers: list[str] = []
    for index, station in enumerate(results):
        left, top = positions[index % len(positions)]
        availability = station.get("availability", {})
        parking = station.get("parking_free")
        parking_text = "무료 주차" if parking is True else "무료 주차 아님" if parking is False else "주차 정보 확인 필요"
        connector_text = " · ".join("급속" if item == "FAST" else "완속" for item in station.get("connector_types", [])) or "타입 확인 필요"
        pop_rows = "".join((
            f'<div class="map-pop-row"><span>시설 유형</span><b>{escape(station.get("facility_type", "확인 필요"))}</b></div>',
            f'<div class="map-pop-row"><span>충전기</span><b>{escape(connector_text)}</b></div>',
            f'<div class="map-pop-row"><span>충전 상태</span><b>{escape(availability_label(station))}</b></div>',
            f'<div class="map-pop-row"><span>이용 시간</span><b>{escape(station.get("use_time") or "확인 필요")}</b></div>',
            f'<div class="map-pop-row"><span>주차</span><b>{parking_text}</b></div>',
        ))
        name = escape(station.get("name", "충전소"))
        availability_text = escape(availability_label(station))
        markers.append(
            f'<div class="map-marker" style="left:{left}%;top:{top}%"><button class="map-pin" onclick="this.parentElement.classList.toggle(\'open\')" aria-label="{name} 상세 보기">⚡</button><div class="map-hover"><b>{name}</b><span>{availability_text}</span></div><div class="map-pop"><div class="map-pop-title">{name}</div>{pop_rows}<div class="map-pop-note">환경공단 상태 · {escape(str(station.get("reported_at") or "갱신 시각 확인 필요"))}</div></div></div>'
        )
    applied = request or {}
    center = applied.get("center", {})
    source = center.get("source", "")
    label = "강남역 기준" if source == "initial_default" else "선택한 위치 기준" if request else "장소명을 입력해 주세요"
    javascript_key = os.environ.get("KAKAO_JAVASCRIPT_KEY", "").strip().strip("\"").strip("'")
    fallback_html = f'<div id="map-fallback" style="position:absolute;inset:0"><div class="map-grid"></div><div class="radius-ring"></div><div class="center-dot"></div>{"".join(markers)}</div>'
    if javascript_key:
        station_payload: list[dict[str, Any]] = []
        for station in results:
            location = station.get("location", {})
            try:
                latitude, longitude = float(location["lat"]), float(location["lng"])
            except (KeyError, TypeError, ValueError):
                continue
            availability = availability_label(station)
            types = " · ".join("급속" if item == "FAST" else "완속" for item in station.get("connector_types", [])) or "타입 확인 필요"
            parking = station.get("parking_free")
            parking_text = "무료 주차" if parking is True else "무료 주차 아님" if parking is False else "주차 정보 확인 필요"
            detail = (
                f'<div class="map-pop-title">{escape(station.get("name", "충전소"))}</div>'
                f'<div class="map-pop-row"><span>충전기</span><b>{escape(types)}</b></div>'
                f'<div class="map-pop-row"><span>충전 상태</span><b>{escape(availability)}</b></div>'
                f'<div class="map-pop-row"><span>이용 시간</span><b>{escape(station.get("use_time") or "확인 필요")}</b></div>'
                f'<div class="map-pop-row"><span>주차</span><b>{parking_text}</b></div>'
            )
            station_payload.append({"lat": latitude, "lng": longitude, "name": station.get("name", "충전소"), "summary": availability, "detail": detail})
        stations_json = json.dumps(station_payload, ensure_ascii=False).replace("</", "<\\/")
        center_lat = center.get("lat", 37.4980)
        center_lng = center.get("lng", 127.0270)
        return MAP_CSS + f'''<div class="map-shell">{fallback_html}<div id="kakao-map" style="position:absolute;inset:0"></div><div id="map-status" class="map-label">{label} · 카카오 지도<br>충전 상태는 환경공단 API 기준입니다.</div><div class="map-legend">⚡ 충전소 · hover 요약 / click 상세 정보</div></div><script>const stations={stations_json};const fallback=document.getElementById('map-fallback');const statusLabel=document.getElementById('map-status');let mapReady=false;function showFallback(message){{document.getElementById('kakao-map').style.display='none';fallback.style.display='block';statusLabel.innerHTML=message;}}function renderKakaoMap(){{try{{const maps=window.kakao.maps;const map=new maps.Map(document.getElementById('kakao-map'),{{center:new maps.LatLng({center_lat},{center_lng}),level:6}});stations.forEach(function(item){{const marker=new maps.Marker({{position:new maps.LatLng(item.lat,item.lng),map:map}});const info=new maps.InfoWindow({{removable:true}});maps.event.addListener(marker,'mouseover',function(){{info.setContent('<div class="map-hover" style="visibility:visible;opacity:1;position:static;transform:none"><b>'+item.name+'</b><span>'+item.summary+'</span></div>');info.open(map,marker);}});maps.event.addListener(marker,'mouseout',function(){{info.close();}});maps.event.addListener(marker,'click',function(){{info.setContent('<div class="map-pop" style="visibility:visible;opacity:1;position:static;transform:none">'+item.detail+'</div>');info.open(map,marker);}});}});mapReady=true;fallback.style.display='none';}}catch(error){{showFallback('카카오 지도 초기화에 실패했습니다.<br>카카오 콘솔에 http://127.0.0.1:8501 을 등록해 주세요.');}}}}const sdk=document.createElement('script');sdk.src='https://dapi.kakao.com/v2/maps/sdk.js?appkey={escape(javascript_key)}&autoload=false';sdk.onload=function(){{if(window.kakao&&window.kakao.maps){{window.kakao.maps.load(renderKakaoMap);}}else{{showFallback('카카오 지도 SDK를 불러오지 못했습니다. JavaScript 키를 확인해 주세요.');}}}};sdk.onerror=function(){{showFallback('카카오 지도 SDK 연결에 실패했습니다. JavaScript 키와 등록 도메인을 확인해 주세요.');}};document.head.appendChild(sdk);window.setTimeout(function(){{if(!mapReady){{showFallback('카카오 지도 연결을 기다리고 있습니다.<br>카카오 콘솔에 http://127.0.0.1:8501 을 등록해 주세요.');}}}},7000);</script>'''
    return MAP_CSS + f'<div class="map-shell">{fallback_html}<div class="map-label">{label} · 예시 지도<br>실제 카카오 지도 키·도메인 연결 전 화면입니다.</div><div class="map-legend">⚡ 충전소 · hover 요약 / click 상세 정보</div></div>'


def render_station_cards(results: list[dict[str, Any]]) -> None:
    st.markdown(f"**충전소 {len(results)}곳**")
    if not results:
        st.info("조건에 맞는 충전소를 찾지 못했습니다.")
        return
    for station in results:
        availability = station.get("availability", {})
        state = availability.get("state", "UNAVAILABLE")
        tone = "ok" if state == "AVAILABLE" else "warn"
        types = " · ".join("급속" if item == "FAST" else "완속" for item in station.get("connector_types", []))
        st.markdown(
            '<div class="station-card"><div class="station-name">' + escape(station.get("name", "충전소"))
            + '</div><div class="station-address">' + escape(station.get("address", "주소 확인 필요"))
            + '</div><div class="station-meta"><span class="chip">' + escape(station.get("facility_type", "시설 유형 확인 필요"))
            + '</span><span class="chip">' + escape(types or "타입 확인 필요")
            + '</span><span class="chip">직선 ' + f'{station.get("distance_km", 0):.1f} km' + '</span></div><div class="status-line"><span class="chip '
            + tone + '">' + escape(availability_label(station)) + '</span></div></div>', unsafe_allow_html=True,
        )


def choose_sidebar_place(candidate: dict[str, Any]) -> None:
    st.session_state.selected_place = candidate
    st.session_state.place_query = candidate["name"]
    st.session_state.suggestion_query = candidate["name"]
    st.session_state.place_suggestions = []
    st.session_state.suggestion_error = None


def search_payload(place: dict[str, Any], radius: int, connector_labels: list[str]) -> dict[str, Any]:
    location = place["location"]
    region_filters = [f"zscode:{place['district_code']}"] if place.get("district_code") else []
    return {
        "center": {"lat": location["lat"], "lng": location["lng"], "source": "kakao_candidate"},
        "radius_km": radius,
        "connector_types": [CONNECTOR_CODES[item] for item in connector_labels],
        "region_filters": region_filters,
    }


def render_direct_search() -> None:
    query = st.text_input("검색 중심", placeholder="장소명 입력 (예: 강남역, 서울시청)", key="place_query")
    normalized_query = query.strip()
    if normalized_query != st.session_state.suggestion_query:
        st.session_state.suggestion_query = normalized_query
        st.session_state.selected_place = None
        st.session_state.place_suggestions = []
        st.session_state.suggestion_error = None
        if len(normalized_query) >= 2:
            try:
                st.session_state.place_suggestions = API.suggest_places(normalized_query, access_token())
            except ApiError as error:
                st.session_state.suggestion_error = error.message
    if normalized_query and len(normalized_query) < 2:
        st.caption("장소명을 두 글자 이상 입력하면 카카오 장소 후보를 보여줍니다.")
    if st.session_state.suggestion_error:
        st.caption(f"장소 후보를 가져오지 못했습니다: {st.session_state.suggestion_error}")
    elif st.session_state.place_suggestions:
        st.caption("카카오 장소 후보")
        for candidate in st.session_state.place_suggestions:
            st.button(
                f"{candidate['name']}\n{candidate['category']} · {candidate['address']}",
                key=f"sidebar-place-{candidate['candidate_id']}",
                use_container_width=True,
                on_click=choose_sidebar_place,
                args=(candidate,),
            )
    selected_place = st.session_state.selected_place
    if selected_place:
        st.success(f"선택한 장소: {selected_place['name']} · {selected_place['address']}")
    connector_labels = st.multiselect("충전기 타입", ["급속", "완속"], default=["급속", "완속"])
    radius = st.radio("검색 반경", [1, 3, 5], index=1, horizontal=True, format_func=lambda value: f"{value} km")
    if st.button("충전소 검색", type="primary", use_container_width=True):
        if selected_place is None:
            if st.session_state.suggestion_error:
                st.error("카카오 장소 후보 인증/연결에 실패했습니다. KAKAO_REST_API_KEY를 확인한 뒤 다시 시도해 주세요.")
                return
            st.warning("장소명을 입력한 뒤 아래 카카오 장소 후보 중 하나를 선택해 주세요.")
            return
        if not connector_labels:
            st.warning("충전기 타입을 하나 이상 선택해 주세요.")
            return
        try:
            set_search_response(API.search(search_payload(selected_place, radius, connector_labels), access_token()))
            st.rerun()
        except ApiError as error:
            st.error(error.message)


def render_chat() -> None:
    for item in st.session_state.chat:
        with st.chat_message(item["role"], avatar="⚡" if item["role"] == "assistant" else "👤"):
            st.markdown(item["content"])
    pending = st.session_state.pending_plan
    if pending and pending.get("status") == "AWAITING_LOCATION_CONFIRMATION":
        st.caption("카카오 장소 후보 · 실제 충전 상태 조회 전")
        candidates = pending.get("candidates", [])
        for candidate in candidates:
            st.markdown(f"**{candidate['name']}** · {candidate['category']}  \n{candidate['address']}")
        suggested = pending.get("suggested_candidate_id")
        if st.button("1순위 장소 기준으로 충전소 찾기", type="primary", use_container_width=True):
            try:
                response = API.confirm(pending["request_id"], access_token(), suggested)
                set_search_response(response)
                st.session_state.chat.append({"role": "assistant", "content": "1순위 장소를 기준으로 충전소를 찾았습니다."})
                st.rerun()
            except ApiError as error:
                st.error(error.message)
    elif pending and pending.get("status") == "AWAITING_CONFIRMATION":
        request = pending.get("search_request", {})
        if st.button("이 조건으로 충전소 찾기", type="primary", use_container_width=True):
            try:
                set_search_response(API.confirm(pending["request_id"], access_token()))
                st.session_state.chat.append({"role": "assistant", "content": "확인한 조건으로 충전소를 찾았습니다."})
                st.rerun()
            except ApiError as error:
                st.error(error.message)
        st.caption(f"반경 {request.get('radius_km', 3)} km · 급속·완속 조건")
    prompt = st.chat_input("예: 서울, 강남역 3 km 급속 충전소")
    if prompt:
        st.session_state.chat.append({"role": "user", "content": prompt})
        try:
            response = API.plan(prompt, access_token())
            st.session_state.pending_plan = response
            st.session_state.chat.append({"role": "assistant", "content": response["message"]})
        except ApiError as error:
            st.session_state.chat.append({"role": "assistant", "content": error.message})
        st.rerun()


def render_status_demo() -> None:
    labels = {1: "결과 없음", 2: "정보 지연", 3: "요청 제한", 4: "제공자 인증 만료", 5: "AI 챗 연결 실패"}
    with st.popover("상태 시연"):
        st.caption("테스트 전용 `/boom/1`~`/boom/5`")
        scenario = st.selectbox("시나리오", list(labels), format_func=lambda item: f"boom/{item} · {labels[item]}")
        if st.button("상태 적용", use_container_width=True):
            try:
                payload = API.boom(scenario, access_token())
                level = st.info if scenario in (1, 2, 4) else st.warning
                level(f"[시연] {payload['code']} · {payload['message']}")
            except ApiError as error:
                payload = error.payload or {}
                st.error(f"[시연] {payload.get('code', 'ERROR')} · {error.message}")


def render_dashboard() -> None:
    role = st.session_state.role
    top, back = st.columns([7, 2])
    with top:
        st.markdown("## 운영 대시보드")
        st.caption("운영 개요 · 서비스 운영 · 배포 · 감사 이력 · 화면 시연 데이터")
    with back:
        if st.button("← 탐색으로", use_container_width=True):
            st.session_state.view = "search"
            st.rerun()
    overview, service, history = st.tabs(["운영 개요", "서비스 운영", "배포 · 감사 이력"])
    with overview:
        st.markdown('<div class="dashboard-hero">현재 화면의 수치와 이력은 초기 1.0 시연 데이터입니다. 실제 운영 시스템을 변경하지 않습니다.</div>', unsafe_allow_html=True)
        columns = st.columns(4)
        for column, label, value in zip(columns, ("요청 성공률", "재시도율", "안전 응답", "최근 배포"), ("98.2%", "6.4%", "3.1%", "성공")):
            with column:
                st.markdown(f'<div class="metric-label">{label}</div><div class="metric-value">{value}</div>', unsafe_allow_html=True)
    with service:
        left, right = st.columns(2)
        with left:
            st.markdown("#### 외부 API · 데이터 품질")
            for provider, status in (("카카오 장소", "정상"), ("환경공단 충전기", "정상"), ("Cache / Circuit Breaker", "대기")):
                st.markdown(f'<div class="detail-row"><span>{provider}</span><b>{status}</b></div>', unsafe_allow_html=True)
        with right:
            st.markdown("#### 에이전트 · 재시도")
            for stage, value in (("Planner", "조건 구조화"), ("Executor", "출처 조회"), ("Critic", "품질 검증"), ("Memory Keeper", "Handoff 보존")):
                st.markdown(f'<div class="detail-row"><span>{stage}</span><b>{value}</b></div>', unsafe_allow_html=True)
        first, second = st.columns(2)
        with first:
            if st.button("예시 요청 재처리", use_container_width=True):
                st.info("시연용 재처리 상태만 표시했습니다. 실제 API를 호출하지 않았습니다.")
        with second:
            if st.button("예시 캐시 갱신", use_container_width=True):
                st.info("시연용 캐시 갱신 상태만 표시했습니다. 실제 API를 호출하지 않았습니다.")
    with history:
        st.markdown("#### 배포 · 감사 이력")
        st.dataframe([{"실행": "#104", "단계": "test → build → deploy", "결과": "성공"}, {"실행": "#103", "단계": "test", "결과": "차단"}], hide_index=True, use_container_width=True)
        if st.button("재시도 횟수 정책 1/2/3회", use_container_width=True):
            if role == "상급 관리자":
                st.success("상급 관리자 시연: 정책 선택 화면을 표시할 수 있습니다. 실제 정책은 변경하지 않았습니다.")
            else:
                role_dialog("상급 관리자 전용 기능입니다.", "이 버튼은 상급 관리자 시연 역할에서만 사용할 수 있습니다.")
        if st.button("손님·하급 관리자 역할 변경", use_container_width=True):
            if role == "상급 관리자":
                st.success("상급 관리자 시연: 역할 전이 UI만 표시합니다. 실제 계정은 변경하지 않습니다.")
            else:
                role_dialog("상급 관리자 전용 기능입니다.", "이 버튼은 상급 관리자 시연 역할에서만 사용할 수 있습니다.")


def render_search() -> None:
    title, actions = st.columns([7, 3], vertical_alignment="center")
    with title:
        st.markdown('<div class="brand-row"><div class="brand-bolt">⚡</div><div><div class="brand-name">ChargePin</div><div class="brand-sub">서울 전기차 충전 자리 안내</div></div></div>', unsafe_allow_html=True)
    with actions:
        st.caption(f"로그인 역할 · **{st.session_state.role}**")
        dashboard, signout = st.columns(2)
        with dashboard:
            open_dashboard = st.button("운영 대시보드", use_container_width=True)
        with signout:
            sign_out = st.button("로그아웃", use_container_width=True)
        if sign_out:
            logout()
        if open_dashboard:
            if st.session_state.role == "손님":
                role_dialog("관리자 전용 화면입니다.", "운영 대시보드는 관리자 시연 역할에서 볼 수 있습니다.")
            else:
                st.session_state.view = "dashboard"
                st.rerun()
    st.divider()
    left, right = st.columns([3.25, 8], gap="medium")
    with left:
        st.markdown('<div class="shell-card"><div class="search-kicker">CHARGEPIN</div><div class="search-title">충전 장소 찾기</div><div class="search-copy">직접 고르거나 대화로 찾아보세요.</div>', unsafe_allow_html=True)
        render_status_demo()
        mode = st.radio("검색 방식", ["탐색", "AI 챗"], horizontal=True, label_visibility="collapsed", key="mode")
        if mode == "탐색":
            render_direct_search()
        else:
            render_chat()
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        request = st.session_state.request
        if request:
            types = "급속·완속" if len(request.get("connector_types", [])) == 2 else "선택 타입"
            st.markdown(f'<div class="summary">적용 조건 · 반경 {request.get("radius_km", 3)} km · {types} · 충전소 검색</div>', unsafe_allow_html=True)
        if st.session_state.notice:
            st.warning(st.session_state.notice)
        st.iframe(
            map_html(st.session_state.results, request),
            height=535,
            alt="카카오 지도 기반 충전소 위치와 충전 가능 상태",
        )
        render_station_cards(st.session_state.results)


def main() -> None:
    init_state()
    st.markdown(STYLES, unsafe_allow_html=True)
    if not access_token():
        render_login()
        return
    load_default_once()
    if st.session_state.view == "dashboard":
        render_dashboard()
    else:
        render_search()


if __name__ == "__main__":
    main()
