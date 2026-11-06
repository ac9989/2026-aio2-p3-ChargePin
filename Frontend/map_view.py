"""Kakao map presentation used by the ChargePin search screen."""
from __future__ import annotations

import json
import os
from html import escape
from typing import Any


MAP_STYLE = r"""<style>
@font-face{font-family:"Pretendard";src:url("/app/static/fonts/PretendardVariable.woff2") format("woff2");font-weight:45 920;font-display:swap}
*{box-sizing:border-box}body{margin:0;font-family:"Pretendard","Malgun Gothic",sans-serif;color:#222831}
.map-shell{position:relative;height:700px;overflow:hidden;border:1px solid #e1e6e9;border-radius:18px;background:#eef1f2}
#kakao-map{position:absolute;inset:0}.map-fallback{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:#f0f2f3}
.map-fallback span{max-width:78%;padding:16px 20px;background:#fff;border-radius:12px;color:#6b7783;font-size:14px;box-shadow:0 8px 24px #27344314}
.map-badge{position:absolute;left:16px;bottom:16px;z-index:5;max-width:calc(100% - 32px);padding:10px 13px;background:#fff;border:1px solid #edf0f2;border-radius:10px;box-shadow:0 4px 18px #202c391c;font-size:12px;line-height:1.55;color:#697783;pointer-events:none}
.map-badge strong{display:block;color:#252b32;font-size:13px}
.map-status{padding:9px 4px 0;color:#79848f;font-size:12px;line-height:1.45}
.cp-map-popup{font-family:"Pretendard","Malgun Gothic",sans-serif;min-width:220px;max-width:280px;padding:13px 15px;color:#252b32;font-size:12px;line-height:1.5}
.cp-map-popup strong{display:block;font-size:14px;margin-bottom:8px}
.cp-map-row{display:flex;justify-content:space-between;gap:16px;padding:3px 0}.cp-map-row span{color:#72808d}.cp-map-row b{text-align:right;font-weight:600}
.cp-map-hover{font-family:"Pretendard","Malgun Gothic",sans-serif;min-width:150px;padding:9px 12px;color:#252b32;font-size:12px;line-height:1.5}
.cp-map-hover strong{display:block;font-size:13px}
@media(max-width:700px){.map-shell{height:520px}.map-badge{bottom:12px;left:12px}}
</style>"""


def build_map_html(results: list[dict[str, Any]], request: dict[str, Any] | None,
                   selected_station: str | None, availability_label: Any) -> str:
    selected = next((row for row in results
                     if str(row.get("facility_id") or "") == str(selected_station or "")), None)
    center = (request or {}).get("center") or {}
    focus = (selected or {}).get("location") or center
    try:
        latitude = float(focus.get("lat", 37.498))
        longitude = float(focus.get("lng", 127.027))
    except (TypeError, ValueError):
        latitude, longitude = 37.498, 127.027
    key = os.environ.get("KAKAO_JAVASCRIPT_KEY", "").strip().strip("\"").strip("'")
    data = []
    for station in results:
        location = station.get("location") or {}
        try:
            lat, lng = float(location["lat"]), float(location["lng"])
        except (KeyError, TypeError, ValueError):
            continue
        name = escape(str(station.get("name") or "충전소"))
        state = escape(str(availability_label(station)))
        types = " · ".join("급속" if item == "FAST" else "완속" for item in station.get("connector_types", [])) or "확인 필요"
        parking = station.get("parking_free")
        parking_label = "무료 주차" if parking is True else "무료 주차 아님" if parking is False else "확인 필요"
        fields = [
            ("주소", station.get("address") or "확인 필요"),
            ("시설 유형", station.get("facility_type") or "확인 필요"),
            ("충전 속도", types),
            ("충전 상태", availability_label(station)),
            ("이용 시간", station.get("use_time") or "확인 필요"),
            ("주차", parking_label),
            ("이용 제한", station.get("restriction_detail") or "확인 필요"),
            ("상태 갱신", station.get("reported_at") or "확인 필요"),
        ]
        detail = '<div class="cp-map-popup"><strong>' + name + '</strong>' + "".join(
            '<div class="cp-map-row"><span>' + escape(str(k)) + '</span><b>'
            + escape(str(v)) + '</b></div>' for k, v in fields) + '</div>'
        hover = '<div class="cp-map-hover"><strong>' + name + '</strong>' + state + '</div>'
        data.append({"lat": lat, "lng": lng, "detail": detail, "hover": hover,
                     "selected": bool(selected_station and str(station.get("facility_id") or "") == str(selected_station))})
    badge = ""
    if request:
        speed = " · ".join("급속" if item == "FAST" else "완속" for item in request.get("connector_types", []))
        try:
            radius = float(request.get("radius_km"))
            range_text = f"검색 범위 {radius * 2:g} km (반경 {radius:g} km)"
        except (TypeError, ValueError):
            range_text = "검색 범위 확인 필요"
        badge = '<strong>' + escape(range_text) + ' · ' + escape(speed or "전체") + '</strong>'
    badge += "충전소 마커를 선택하면 상세 정보를 볼 수 있어요"
    if not key:
        return (MAP_STYLE + '<div class="map-shell"><div class="map-fallback"><span>카카오 지도 연결을 확인해 주세요.</span>'
                '</div><div class="map-badge">' + badge + '</div></div>'
                '<div class="map-status">지도 연결 전 · 충전소 정보는 결과 목록에서 확인할 수 있어요.</div>')
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    key_json = json.dumps(key, ensure_ascii=True)
    javascript = r"""
<script>
const stations=__STATIONS__,appKey=__KEY__,fallback=document.getElementById("map-fallback");
const status=document.getElementById("map-status");let ready=false,active=null;
function fail(message){document.getElementById("kakao-map").style.display="none";fallback.style.display="flex";status.textContent=message;}
function startMap(){try{
  const maps=window.kakao.maps;
  const map=new maps.Map(document.getElementById("kakao-map"),{center:new maps.LatLng(__LAT__,__LNG__),level:5});
  map.addControl(new maps.ZoomControl(),maps.ControlPosition.RIGHT);
  const svg='<svg xmlns="http://www.w3.org/2000/svg" width="36" height="45" viewBox="0 0 36 45"><path d="M18 2C9.2 2 2 9.2 2 18c0 11 16 25 16 25s16-14 16-25C34 9.2 26.8 2 18 2Z" fill="#252b32" stroke="white" stroke-width="2.5"/><path d="M19.5 7 12 19h5l-1 8 8-12h-5z" fill="#FFD14D"/></svg>';
  const markerUrl="data:image/svg+xml;charset=utf-8,"+encodeURIComponent(svg);
  const markerImage=new maps.MarkerImage(markerUrl,new maps.Size(36,45),{offset:new maps.Point(18,44)});
  const hover=new maps.InfoWindow();
  const detail=new maps.InfoWindow({removable:true});
  stations.forEach(function(item){
    const marker=new maps.Marker({position:new maps.LatLng(item.lat,item.lng),map:map,image:markerImage});
    maps.event.addListener(marker,"mouseover",function(){if(active!==marker){hover.setContent(item.hover);hover.open(map,marker);}});
    maps.event.addListener(marker,"mouseout",function(){hover.close();});
    maps.event.addListener(marker,"click",function(){hover.close();detail.close();detail.setContent(item.detail);detail.open(map,marker);active=marker;});
    if(item.selected){detail.setContent(item.detail);detail.open(map,marker);active=marker;}
  });
  document.getElementById("kakao-map").style.display="block";fallback.style.display="none";ready=true;
}catch(error){fail("카카오 지도를 표시하지 못했어요. JavaScript 키와 등록 도메인을 확인해 주세요.");}}
const script=document.createElement("script");
script.src="https://dapi.kakao.com/v2/maps/sdk.js?appkey="+encodeURIComponent(appKey)+"&autoload=false";
script.onload=function(){if(window.kakao&&window.kakao.maps){window.kakao.maps.load(startMap)}else{fail("카카오 지도 SDK를 불러오지 못했어요.")}};
script.onerror=function(){fail("카카오 지도 연결을 확인해 주세요.")};document.head.appendChild(script);
window.setTimeout(function(){if(!ready)fail("카카오 지도 응답이 지연되고 있어요.")},8000);
</script>"""
    javascript = (javascript.replace("__STATIONS__", payload).replace("__KEY__", key_json)
                  .replace("__LAT__", str(latitude)).replace("__LNG__", str(longitude)))
    return (MAP_STYLE + '<div class="map-shell"><div id="map-fallback" class="map-fallback"><span>지도를 불러오는 중이에요.</span>'
            '</div><div id="kakao-map"></div><div class="map-badge">' + badge + '</div></div>'
            '<div id="map-status" class="map-status">지도 · 카카오 &nbsp;|&nbsp; 충전 정보 · 환경공단</div>'
            + javascript)
