"""Kakao map presentation used by the ChargePin search screen."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
import json
import os
from typing import Any


MAP_STYLE = r"""<style>
@font-face{font-family:"Pretendard";src:url("/app/static/fonts/PretendardVariable.woff2") format("woff2");font-weight:45 920;font-display:swap}
*{box-sizing:border-box}body{margin:0;font-family:"Pretendard","Malgun Gothic",sans-serif;color:#222831}
.map-shell{position:relative;height:700px;overflow:hidden;border:1px solid #e1e6e9;border-radius:18px;background:#eef1f2}
#kakao-map{position:absolute;inset:0}.map-fallback{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:#f0f2f3}
.map-fallback span{max-width:78%;padding:16px 20px;background:#fff;border-radius:12px;color:#6b7783;font-size:14px;box-shadow:0 8px 24px #27344314}
.map-badge{position:absolute;left:16px;bottom:16px;z-index:5;max-width:calc(100% - 32px);padding:10px 13px;background:#fff;border:1px solid #edf0f2;border-radius:10px;box-shadow:0 4px 18px #202c391c;font-size:12px;line-height:1.55;color:#697783;pointer-events:none}
.map-badge strong{display:block;color:#252b32;font-size:13px}
.map-legend{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;margin-top:7px;padding-top:7px;border-top:1px solid #edf0f2}
.map-legend-item{display:inline-flex;align-items:center;gap:5px;color:#52616d;white-space:nowrap}
.map-legend-symbol{display:inline-grid;place-items:center;width:19px;height:19px;border-radius:50%;color:#fff;font-weight:700;font-size:11px;line-height:1}
.map-legend-symbol.available{background:#f5b51b;color:#252b32}.map-legend-symbol.unknown{background:#5c6269}
.map-notice{position:absolute;top:14px;left:14px;z-index:5;max-width:min(380px,calc(100% - 80px));max-height:32%;overflow:auto;box-sizing:border-box;padding:10px 13px;background:#fffdf5;border:1px solid #ead49a;border-radius:11px;box-shadow:0 4px 16px #202c391c;color:#665b40;font:12px/1.5 "Pretendard","Malgun Gothic",sans-serif;overflow-wrap:anywhere}
.map-notice strong{display:block;color:#7d5b12;font-size:13px;margin-bottom:3px}.map-notice ul{margin:0;padding-left:16px}.map-notice li+li{margin-top:3px}
.map-zoom{position:absolute;z-index:6;top:16px;right:16px;display:flex;flex-direction:column;background:#fff;border:1px solid #e1e6e9;border-radius:12px;box-shadow:0 5px 18px #202c391c;overflow:hidden}
.map-zoom[hidden]{display:none}.map-zoom button{display:grid;place-items:center;width:38px;height:38px;padding:0;border:0;background:#fff;color:#28323b;font:400 23px/1 Arial,sans-serif;cursor:pointer}.map-zoom button+button{border-top:1px solid #e9edf0}.map-zoom button:hover{background:#f2f4f6}.map-zoom button:focus-visible{outline:2px solid #e2af32;outline-offset:-3px}
.map-status{padding:9px 4px 0;color:#79848f;font-size:12px;line-height:1.45}
.cp-map-popup{position:relative;width:300px;max-width:calc(100vw - 32px);padding:16px;background:#fff;border:1px solid #e1e6e9;border-radius:15px;box-shadow:0 12px 35px #1825322b;color:#252b32;font:13px/1.5 "Pretendard","Malgun Gothic",sans-serif;word-break:keep-all;overflow-wrap:anywhere}
.cp-map-popup-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.cp-map-popup-head strong{font-size:15px;line-height:1.4;font-weight:750;border-left:3px solid #f5a623;padding-left:9px}.cp-map-close{display:grid;place-items:center;flex:none;width:28px;height:28px;margin:-4px -5px 0 0;padding:0;border:0;border-radius:8px;background:#f2f4f6;color:#53616d;font:20px/1 Arial,sans-serif;cursor:pointer}.cp-map-close:hover{background:#e7ebee}.cp-map-close:focus-visible{outline:2px solid #d6a626}
.cp-map-address{margin:5px 0 11px;color:#788694;font-size:12px;line-height:1.5}.cp-map-fields{border-top:1px solid #edf0f2;padding-top:8px}.cp-map-row{display:grid;grid-template-columns:68px minmax(0,1fr);gap:8px;padding:4px 0;align-items:start}.cp-map-row span{color:#82909d}.cp-map-row b{text-align:right;color:#303b45;font-weight:600;line-height:1.5}.cp-map-row b.warn{color:#a4650c}.cp-map-row b.available{color:#087a5d}.cp-map-row b.speed{color:#b76512}
.cp-map-hover{width:220px;max-width:calc(100vw - 40px);white-space:normal;overflow-wrap:anywhere;word-break:keep-all;background:#fff;border:1px solid #dce4e9;border-radius:10px;box-shadow:0 4px 14px #172f3b26;font-family:"Pretendard","Malgun Gothic",sans-serif;min-width:150px;padding:9px 12px;color:#252b32;font-size:12px;line-height:1.5}.cp-map-hover strong{display:block;font-size:13px}
@media(max-width:700px){.map-shell{height:520px}.map-badge{bottom:12px;left:12px}.map-notice{top:12px;left:12px;max-width:calc(100% - 72px)}.map-zoom{top:12px;right:12px}}
</style>"""


# When the map iframe has focus, send only a static event to its parent page.
MAP_CAPTURE_FORWARDER = r"""<script>
(() => {
  function onKey(event) {
    if (event.key === "PrintScreen" || event.code === "PrintScreen" || event.keyCode === 44) {
      window.parent.postMessage({type:"chargepin:printscreen"}, "*");
    }
  }
  document.addEventListener("keydown", onKey, true);
  document.addEventListener("keyup", onKey, true);
})();
</script>"""


def format_reported_at(value: Any) -> str:
    if not value:
        return "확인 필요"
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone(timedelta(hours=9))).strftime("%Y.%m.%d %H:%M KST")
    return parsed.strftime("%Y.%m.%d %H:%M")


def build_map_html(results: list[dict[str, Any]], request: dict[str, Any] | None,
                   selected_station: str | None, availability_label: Any,
                   quality_notices: list[str] | None = None) -> str:
    selected = next((row for row in results
                     if str(row.get("facility_id") or "") == str(selected_station or "")), None)
    center = (request or {}).get("center") or {}
    focus = (selected or {}).get("location") or center
    try:
        latitude = float(focus.get("lat", 37.498))
        longitude = float(focus.get("lng", 127.027))
    except (TypeError, ValueError):
        latitude, longitude = 37.498, 127.027
    key = os.environ.get("KAKAO_JAVASCRIPT_KEY", "").strip().strip(chr(34)).strip(chr(39))
    data = []
    for station in results:
        location = station.get("location") or {}
        try:
            lat, lng = float(location["lat"]), float(location["lng"])
        except (KeyError, TypeError, ValueError):
            continue
        name = escape(str(station.get("name") or "충전소"))
        state = str(availability_label(station))
        types = " · ".join("급속" if item == "FAST" else "완속" for item in station.get("connector_types", [])) or "확인 필요"
        parking = station.get("parking_free")
        parking_label = "무료 주차" if parking is True else "무료 주차 아님" if parking is False else "확인 필요"
        address = escape(str(station.get("address") or "주소 확인 필요"))
        fields = [
            ("시설 유형", station.get("facility_type") or "확인 필요"),
            ("충전 속도", types),
            ("충전 상태", state),
            ("이용 시간", station.get("use_time") or "확인 필요"),
            ("주차", parking_label),
            ("이용 제한", station.get("restriction_detail") or "확인 필요"),
            ("상태 갱신", format_reported_at(station.get("reported_at"))),
        ]
        rows = "".join('<div class="cp-map-row"><span>' + escape(str(label)) + '</span><b'
                       + (' class="available"' if label == "충전 상태" and isinstance((station.get("availability") or {}).get("available_chargers"), int) and (station.get("availability") or {}).get("available_chargers") > 0 else ' class="warn"' if label == "충전 상태" and "지연" in str(value) else ' class="speed"' if label == "충전 속도" else '')
                       + '>' + escape(str(value)) + '</b></div>' for label, value in fields)
        detail = ('<div class="cp-map-popup" role="group" aria-label="충전소 상세 정보">'
                  '<div class="cp-map-popup-head"><strong>' + name + '</strong>'
                  '<button type="button" class="cp-map-close" aria-label="충전소 정보 닫기">×</button></div>'
                  '<div class="cp-map-address">' + address + '</div><div class="cp-map-fields">' + rows + '</div></div>')
        hover = '<div class="cp-map-hover"><strong>' + name + '</strong>' + escape(state) + '</div>'
        data.append({"lat": lat, "lng": lng, "detail": detail, "hover": hover,
                     "available": (station.get("availability") or {}).get("available_chargers"),
                     "selected": bool(selected_station and str(station.get("facility_id") or "") == str(selected_station))})
    badge = ""
    if request:
        speed = " · ".join("급속" if item == "FAST" else "완속" for item in request.get("connector_types", []))
        badge = '<strong>반경 ' + escape(str(request.get("radius_km", "—"))) + ' km · ' + escape(speed or "전체") + '</strong>'
    badge += ('<div class="map-legend" aria-label="지도 마커 범례">'
              '<span class="map-legend-item"><span class="map-legend-symbol available">1</span>숫자 · 이용 가능 대수</span>'
              '<span class="map-legend-item"><span class="map-legend-symbol unknown">⚡</span>0대 또는 정보 확인 필요</span>'
              '</div>')
    notices = [str(item) for item in (quality_notices or []) if item]
    notice = ('<div class="map-notice" role="status"><strong>충전 정보 안내</strong><ul>'
              + ''.join('<li>' + escape(item) + '</li>' for item in notices) + '</ul></div>') if notices else ''
    if not key:
        return (MAP_STYLE + '<div class="map-shell"><div class="map-fallback"><span>카카오 지도 연결을 확인해 주세요.</span>'
                '</div>' + notice + '<div class="map-badge">' + badge + '</div></div>'
                '<div class="map-status">지도 연결 전 · 충전소 정보는 결과 목록에서 확인할 수 있어요.</div>' + MAP_CAPTURE_FORWARDER)
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
  const zoom=document.getElementById("map-zoom");zoom.hidden=false;
  document.getElementById("map-zoom-in").addEventListener("click",function(){map.setLevel(Math.max(1,map.getLevel()-1));});
  document.getElementById("map-zoom-out").addEventListener("click",function(){map.setLevel(Math.min(14,map.getLevel()+1));});
  const svg='<svg xmlns="http://www.w3.org/2000/svg" width="36" height="45" viewBox="0 0 36 45"><path d="M18 2C9.2 2 2 9.2 2 18c0 11 16 25 16 25s16-14 16-25C34 9.2 26.8 2 18 2Z" fill="#252b32" stroke="white" stroke-width="2.5"/><path d="M19.5 7 12 19h5l-1 8 8-12h-5z" fill="#FFD14D"/></svg>';

  let hover=null,detail=null;
  function closeHover(){if(hover){hover.setMap(null);hover=null;}}
  function closeDetail(){if(detail){detail.setMap(null);detail=null;}active=null;}
  function openDetail(item,marker,move){
    closeHover();closeDetail();
    const content=document.createElement("div");content.innerHTML=item.detail;
    content.querySelector(".cp-map-close").addEventListener("click",function(event){event.stopPropagation();closeDetail();});
    detail=new maps.CustomOverlay({position:marker.getPosition(),content:content,xAnchor:0.5,yAnchor:1.18,zIndex:7,clickable:true});
    detail.setMap(map);active=marker;if(move)map.panTo(marker.getPosition());
  }
  stations.forEach(function(item){
    const count = item.available;
    const valid = Number.isInteger(count) && count > 0;
    const icon = valid ? `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="45" viewBox="0 0 36 45"><path d="M18 2C9.2 2 2 9.2 2 18c0 11 16 25 16 25s16-14 16-25C34 9.2 26.8 2 18 2Z" fill="#f5b51b" stroke="white" stroke-width="2.5"/><text x="18" y="24" fill="#252b32" text-anchor="middle" font-family="Arial" font-size="15" font-weight="bold">${count}</text></svg>` : svg.replace("#252b32", "#5c6269").replace("#FFD14D", "#ffffff");
    const markerImage=new maps.MarkerImage("data:image/svg+xml;charset=utf-8,"+encodeURIComponent(icon),new maps.Size(36,45),{offset:new maps.Point(18,44)});
    const marker=new maps.Marker({position:new maps.LatLng(item.lat,item.lng),map:map,image:markerImage});
    maps.event.addListener(marker,"mouseover",function(){if(active!==marker){closeHover();hover=new maps.CustomOverlay({position:marker.getPosition(),content:item.hover,xAnchor:0.5,yAnchor:1.35,zIndex:6});hover.setMap(map);}});
    maps.event.addListener(marker,"mouseout",closeHover);
    maps.event.addListener(marker,"click",function(){openDetail(item,marker,true);});
    if(item.selected)openDetail(item,marker,false);
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
    zoom = ('<div class="map-zoom" id="map-zoom" hidden><button id="map-zoom-in" type="button" aria-label="지도 확대" title="지도 확대">+</button>'
            '<button id="map-zoom-out" type="button" aria-label="지도 축소" title="지도 축소">−</button></div>')
    return (MAP_STYLE + '<div class="map-shell"><div id="map-fallback" class="map-fallback"><span>지도를 불러오는 중이에요.</span>'
            '</div><div id="kakao-map"></div>' + zoom + notice + '<div class="map-badge">' + badge + '</div></div>'
            '<div id="map-status" class="map-status">지도 · 카카오 &nbsp;|&nbsp; 충전 정보 · 환경공단</div>'
            + javascript + MAP_CAPTURE_FORWARDER)
