"""Kakao map component with a clearly labelled preview fallback."""
from __future__ import annotations

import os
from typing import Any

import streamlit as st

from services.preview import CITY_HALL_CENTER, DEFAULT_CENTER, SEOUL_STATION_CENTER, marker_information

_HTML = """
<div class="map-shell">
  <div class="map-canvas" aria-label="검색 중심과 시설 위치"></div>
  <div class="map-notice" aria-live="polite"></div>
  <div class="legend"><span class="charging">● 충전 장소</span><span class="candidate">◌ 장소 후보</span></div>
</div>
"""

_CSS = """
.map-shell { position:relative; width:100%; border:1px solid #DCE8E5; border-radius:20px; overflow:hidden; background:#F5F8F5; box-shadow:0 8px 25px #536d6710; }
.map-canvas { height:620px; position:relative; overflow:hidden; background:#F5F8F5; }
.map-notice { position:absolute; left:14px; top:14px; z-index:5; max-width:75%; border-radius:8px; background:#fff; padding:8px 11px; color:#51412B; font-size:12px; box-shadow:0 2px 10px #1232; }
.legend { position:absolute; left:14px; bottom:14px; display:flex; gap:12px; z-index:5; padding:10px 12px; border-radius:10px; background:#fff; color:#5A472D; font-size:12px; box-shadow:0 2px 10px #1232; flex-wrap:wrap; }
.charging { color:#40331D; } .candidate { color:#78633D; }
.preview-background { position:absolute; inset:0; background:linear-gradient(112deg, transparent 36%, #DCEEF2 36%, #DCEEF2 47%, transparent 47%), linear-gradient(0deg, transparent 39%, #FFFFFF 39%, #FFFFFF 40%, transparent 40%), linear-gradient(90deg, transparent 61%, #FFFFFF 61%, #FFFFFF 62%, transparent 62%), #F3F7F3; }
.radius-ring { position:absolute; width:46%; aspect-ratio:1; left:27%; top:50%; transform:translateY(-50%); border:2px dashed #C3922E; background:#F6D66F24; border-radius:50%; }
.center-point { position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); width:13px; height:13px; background:#3A2D1B; border:2px solid white; border-radius:5px; z-index:2; }
.marker { position:absolute; z-index:3; width:36px; height:36px; transform:translate(-50%,-50%); }
.marker:hover, .marker:focus-within, .marker.selected { z-index:25; }
.pin { position:relative; width:36px; height:36px; border:2px solid white; border-radius:50%; cursor:pointer; color:white; font-weight:800; background:#40331D; box-shadow:0 2px 5px #0003; }
.pin.candidate-pin { color:#40331D; background:white; border:2px dashed #40331D; }
.pin.selected { outline:3px solid #D8AA36; outline-offset:2px; }
.pin:focus-visible { outline:4px solid #D8AA36; outline-offset:3px; }
.pin-info { visibility:hidden; opacity:0; pointer-events:none; position:absolute; left:50%; bottom:calc(100% + 10px); transform:translateX(-50%); box-sizing:border-box; width:240px; padding:13px 14px; border:1px solid #DCE4E9; border-radius:13px; background:#FFF; color:#28323C; box-shadow:0 10px 28px #2433422B; font-family:inherit; }
.marker:hover .pin-info, .marker:focus-within .pin-info, .marker.selected .pin-info { visibility:visible; opacity:1; }
.marker.align-left .pin-info { left:0; right:auto; transform:none; }
.marker.align-right .pin-info { left:auto; right:0; transform:none; }
.marker.tooltip-below .pin-info { top:calc(100% + 10px); bottom:auto; }
.pin-title { font-size:13px; font-weight:750; line-height:1.35; margin-bottom:8px; overflow-wrap:anywhere; }
.pin-row { display:flex; justify-content:space-between; gap:8px; padding:3px 0; font-size:11px; line-height:1.35; }
.pin-row span:first-child { color:#778490; flex:none; }
.pin-row strong { color:#26313C; text-align:right; font-weight:700; overflow-wrap:anywhere; }
.pin-access-detail { margin-top:4px; font-size:11px; line-height:1.4; color:#8A5E12; }
.pin-forecast { margin-top:8px; padding:7px 8px; border-radius:7px; background:#FFF5D7; color:#805B0A; font-size:11px; line-height:1.4; }
.pin-note { margin-top:8px; padding-top:7px; border-top:1px solid #EDF0F2; color:#8A959F; font-size:10px; line-height:1.4; }
@media(max-width:900px) { .map-canvas { height:480px; } }
"""

_JS = """
export default function(component) {
  const { data, parentElement, setTriggerValue } = component;
  const area = parentElement.querySelector('.map-canvas');
  const notice = parentElement.querySelector('.map-notice');
  const center = data.center || {lat:37.498, lng:127.027};
  const cards = Array.isArray(data.cards) ? data.cards : [];
  let tooltipId = 0;
  area.replaceChildren();

  function addLine(parent, label, value) {
    const line = document.createElement('div');
    line.className = 'pin-row';
    const key = document.createElement('span');
    const detail = document.createElement('strong');
    key.textContent = label;
    detail.textContent = value || '확인 필요';
    line.append(key, detail);
    parent.appendChild(line);
  }

  function adjustTooltip(marker) {
    const bounds = area.getBoundingClientRect();
    const point = marker.getBoundingClientRect();
    marker.classList.toggle('align-left', point.left - bounds.left < 125);
    marker.classList.toggle('align-right', bounds.right - point.right < 125);
    const above = point.top - bounds.top;
    const below = bounds.bottom - point.bottom;
    marker.classList.toggle('tooltip-below', above < 245 && below > above);
  }

  function makeMarker(card) {
    const marker = document.createElement('div');
    marker.className = 'marker';
    if (card.id === data.selected) marker.classList.add('selected');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'pin';
    if (card.kind === '후보') button.classList.add('candidate-pin');
    if (card.id === data.selected) button.classList.add('selected');
    button.textContent = card.kind === '후보' ? '후' : '⚡';
    button.setAttribute('aria-label', card.name + ' 상세 정보');

    const popup = document.createElement('div');
    popup.className = 'pin-info';
    popup.id = 'pin-info-' + (++tooltipId);
    popup.setAttribute('role', 'tooltip');
    button.setAttribute('aria-describedby', popup.id);
    const title = document.createElement('div');
    title.className = 'pin-title';
    title.textContent = card.name;
    popup.appendChild(title);
    addLine(popup, '장소 유형', card.site_type);
    addLine(popup, '외부인 이용', card.access);
    if (card.access_detail) {
      const detail = document.createElement('div');
      detail.className = 'pin-access-detail';
      detail.textContent = card.access_detail;
      popup.appendChild(detail);
    }
    addLine(popup, '주차 요금', card.parking_fee);
    addLine(popup, '충전기', card.charger_type);
    addLine(popup, '이용 제한시간', card.usage_limit);
    addLine(popup, '주차 현황', card.parking_status);
    if (card.forecast || card.parking_status === '만차') {
      const forecast = document.createElement('div');
      forecast.className = 'pin-forecast';
      forecast.textContent = card.forecast || '자리 예측 정보 확인 필요';
      popup.appendChild(forecast);
    }
    const note = document.createElement('div');
    note.className = 'pin-note';
    note.textContent = card.is_preview ? '시연 예시 · 주차 요금은 충전 요금과 별도' : '주차 요금은 충전 요금과 별도';
    popup.appendChild(note);
    marker.append(button, popup);

    marker.addEventListener('mouseenter', () => adjustTooltip(marker));
    button.addEventListener('focus', () => adjustTooltip(marker));
    button.addEventListener('click', function(event) {
      event.stopPropagation();
      setTriggerValue('marker_click', card.id);
    });
    return marker;
  }

  function drawExample() {
    notice.textContent = (data.center_label ? data.center_label + ' 기준 · ' : '') + '예시 지도 · 실제 지도가 연결되지 않았어요';
    const bg = document.createElement('div');
    bg.className = 'preview-background';
    const circle = document.createElement('div'); circle.className = 'radius-ring';
    const dot = document.createElement('div'); dot.className = 'center-point';
    area.append(bg, circle, dot);
    const previewPositions = [[34, 38], [66, 36], [31, 61], [68, 62], [52, 47]];
    cards.forEach(function(card, index) {
      const marker = makeMarker(card);
      const position = previewPositions[index % previewPositions.length];
      marker.style.left = position[0] + '%';
      marker.style.top = position[1] + '%';
      area.appendChild(marker);
      requestAnimationFrame(() => adjustTooltip(marker));
    });
  }

  function drawKakao() {
    if (!area.isConnected || !window.kakao || !window.kakao.maps) return;
    window.kakao.maps.load(function() {
      if (!area.isConnected) return;
      area.replaceChildren();
      notice.textContent = '지도: 카카오 · 장소·상태는 예시 데이터';
      const maps = window.kakao.maps;
      const location = new maps.LatLng(center.lat, center.lng);
      const map = new maps.Map(area, {center:location, level:7});
      new maps.Circle({center:location, radius:Number(data.radius || 3) * 1000,
        strokeWeight:2, strokeColor:'#40331D', strokeOpacity:0.8, strokeStyle:'dash',
        fillColor:'#F7CD53', fillOpacity:0.18}).setMap(map);
      const centerDot = document.createElement('div');
      centerDot.style.cssText = 'width:12px;height:12px;background:#3A2D1B;border:2px solid white;border-radius:5px';
      new maps.CustomOverlay({position:location, content:centerDot}).setMap(map);
      for (const card of cards) {
        const lat = Number(card.lat), lng = Number(card.lng);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
        const marker = makeMarker(card);
        marker.style.position = 'relative';
        marker.style.transform = 'none';
        const overlay = new maps.CustomOverlay({
          position:new maps.LatLng(lat,lng), content:marker, xAnchor:0.5, yAnchor:0.5,
          clickable:true, zIndex:3
        });
        overlay.setMap(map);
        marker.addEventListener('mouseenter', () => overlay.setZIndex(25));
        marker.addEventListener('mouseleave', () => overlay.setZIndex(3));
        marker.addEventListener('focusin', () => overlay.setZIndex(25));
        marker.addEventListener('focusout', () => overlay.setZIndex(3));
        requestAnimationFrame(() => adjustTooltip(marker));
      }
      maps.event.addListener(map, 'click', function(event) {
        const point = event.latLng;
        setTriggerValue('map_click', {lat:point.getLat(), lng:point.getLng()});
      });
    });
  }

  if (!data.js_key) {
    drawExample();
  } else if (window.kakao && window.kakao.maps) {
    drawKakao();
  } else {
    notice.textContent = '카카오 지도를 불러오는 중이에요.';
    let script = document.getElementById('ev-kakao-map-sdk');
    if (!script) {
      script = document.createElement('script');
      script.id = 'ev-kakao-map-sdk';
      script.src = 'https://dapi.kakao.com/v2/maps/sdk.js?appkey=' + encodeURIComponent(data.js_key) + '&autoload=false';
      document.head.appendChild(script);
    }
    script.addEventListener('load', drawKakao, {once:true});
    script.addEventListener('error', function() {
      notice.textContent = '카카오 지도를 불러오지 못했어요. 키와 도메인 설정을 확인해 주세요.';
    }, {once:true});
  }
}
"""

_map_component = st.components.v2.component("seoul_ev_map", html=_HTML, css=_CSS, js=_JS)


def show_map(center: tuple[float, float], radius: int, cards: list[dict[str, Any]], selected: str | None):
    map_cards = []
    for item in cards:
        if item.get("latitude") is None or item.get("longitude") is None:
            continue
        map_cards.append({
            "id": item["id"], "name": item["name"], "kind": item["kind"],
            "lat": item["latitude"], "lng": item["longitude"],
            "is_preview": item.get("is_preview") is True,
            **marker_information(item),
        })
    center_label = (
        "서울시청" if center == CITY_HALL_CENTER else
        "서울역" if center == SEOUL_STATION_CENTER else
        "강남역" if center == DEFAULT_CENTER else ""
    )
    return _map_component(
        key="ev_map",
        data={
            "center": {"lat": center[0], "lng": center[1]},
            "center_label": center_label,
            "radius": radius, "cards": map_cards, "selected": selected,
            "js_key": os.environ.get("EV_KAKAO_JS_KEY", "").strip(),
        },
        on_marker_click_change=lambda: None,
        on_map_click_change=lambda: None,
    )
