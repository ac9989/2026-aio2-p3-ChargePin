"""Real Kakao and Korea Environment Corporation provider adapters."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import asin, ceil, cos, radians, sin, sqrt
import json
import os
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from .models import ConnectorType, PlaceCandidate, Point, SearchInput

KST = timezone(timedelta(hours=9))
KECO_BASE_URL = "https://apis.data.go.kr/B552584/EvCharger"
KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
SEOUL_ZCODE = "11"
DISTRICT_CODES = {
    "종로구": "11110", "중구": "11140", "용산구": "11170", "성동구": "11200", "광진구": "11215",
    "동대문구": "11230", "중랑구": "11260", "성북구": "11290", "강북구": "11305", "도봉구": "11320",
    "노원구": "11350", "은평구": "11380", "서대문구": "11410", "마포구": "11440", "양천구": "11470",
    "강서구": "11500", "구로구": "11530", "금천구": "11545", "영등포구": "11560", "동작구": "11590",
    "관악구": "11620", "서초구": "11650", "강남구": "11680", "송파구": "11710", "강동구": "11740",
}
SLOW_TYPES = {"02", "07", "08"}
FAST_TYPES = {"01", "03", "04", "05", "06"}


class ProviderError(RuntimeError):
    """Sanitized upstream error safe to show in API responses."""

    def __init__(self, provider: str, user_message: str, retryable: bool = False) -> None:
        self.provider = provider
        self.user_message = user_message
        self.retryable = retryable
        super().__init__(f"{provider}: {user_message}")


def kst_now() -> datetime:
    return datetime.now(KST).replace(microsecond=0)


def env_secret(name: str) -> str:
    """Read .env values defensively when a developer used optional wrapping quotes."""
    value = os.environ.get(name, "").strip()
    if len(value) >= 2 and value[:1] == value[-1:] and value[:1] in {"\"", "'"}:
        return value[1:-1].strip()
    return value


def distance_km(origin: Point, latitude: float, longitude: float) -> float:
    latitude_delta = radians(latitude - origin.lat)
    longitude_delta = radians(longitude - origin.lng)
    a = sin(latitude_delta / 2) ** 2
    a += cos(radians(origin.lat)) * cos(radians(latitude)) * sin(longitude_delta / 2) ** 2
    return 6371.0 * 2 * asin(min(1.0, sqrt(a)))


def parse_keco_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if len(text) != 14 or not text.isdigit():
        return None
    try:
        return datetime.strptime(text, "%Y%m%d%H%M%S").replace(tzinfo=KST)
    except ValueError:
        return None


def as_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items = payload.get("items", {})
    values = items.get("item", []) if isinstance(items, dict) else []
    if isinstance(values, dict):
        values = [values]
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


def district_code(address: str) -> str | None:
    return next((code for name, code in DISTRICT_CODES.items() if name in address), None)


def connector_type(chger_type: Any) -> ConnectorType | None:
    code = str(chger_type or "").zfill(2)
    if code in SLOW_TYPES:
        return ConnectorType.SLOW
    if code in FAST_TYPES:
        return ConnectorType.FAST
    return None


def facility_type(item: dict[str, Any]) -> str:
    """Avoid presenting opaque provider codes as if they were user-readable facility types."""
    value = str(item.get("kindDetail") or item.get("kind") or "").strip()
    return value if any("가" <= char <= "힣" for char in value) else "시설 유형 확인 필요"


class KakaoPlaceAdapter:
    """Server-side keyword search. The REST key never reaches the Streamlit client."""

    def __init__(self) -> None:
        self._key = env_secret("KAKAO_REST_API_KEY")

    def top_two(self, query: str) -> list[PlaceCandidate]:
        if not self._key:
            raise ProviderError("KAKAO", "카카오 장소 API 키가 설정되지 않았습니다.")
        # Sidebar and chat candidates are the raw Kakao keyword-search ranking.
        # Do not bias by an arbitrary city-centre coordinate, distance, or our own name filter.
        params = urlencode({"query": query, "size": 2})
        request = Request(f"{KAKAO_KEYWORD_URL}?{params}", headers={"Authorization": f"KakaoAK {self._key}", "Accept": "application/json"})
        try:
            with urlopen(request, timeout=7) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code in (401, 403):
                raise ProviderError("KAKAO", "카카오 장소 API 인증을 확인해 주세요.") from error
            if error.code == 429:
                raise ProviderError("KAKAO", "카카오 장소 API 요청이 제한되었습니다. 잠시 후 다시 시도해 주세요.", retryable=True) from error
            raise ProviderError("KAKAO", "카카오 장소 정보를 가져오지 못했습니다.", retryable=True) from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ProviderError("KAKAO", "카카오 장소 응답이 지연되고 있습니다.", retryable=True) from error
        documents = payload.get("documents", [])
        candidates: list[PlaceCandidate] = []
        for document in documents:
            if not isinstance(document, dict):
                continue
            address = str(document.get("road_address_name") or document.get("address_name") or "")
            try:
                location = Point(lat=float(document["y"]), lng=float(document["x"]), source="kakao_candidate")
            except (KeyError, TypeError, ValueError):
                continue
            candidates.append(PlaceCandidate(
                candidate_id=str(document.get("id") or f"kakao-{len(candidates)}"), name=str(document.get("place_name") or "장소명 확인 필요"),
                category=str(document.get("category_name") or "장소"), address=address or "주소 확인 필요", location=location,
                district_code=district_code(address),
            ))
        if not candidates:
            raise ProviderError("KAKAO", "카카오 장소 후보를 찾지 못했습니다.")
        return candidates


class EnvironmentChargerAdapter:
    """KECO charger info/status client with district cache and no browser key exposure."""

    def __init__(self) -> None:
        self._service_key = env_secret("KECO_SERVICE_KEY")
        self._cache_ttl_seconds = int(os.environ.get("KECO_INFO_CACHE_TTL_SECONDS", "600"))
        self._status_cache_ttl_seconds = int(os.environ.get("KECO_STATUS_CACHE_TTL_SECONDS", "30"))
        self._info_cache: dict[str, tuple[datetime, list[dict[str, Any]]]] = {}
        self._status_cache: tuple[datetime, dict[tuple[str, str], dict[str, Any]]] | None = None
        self._lock = Lock()

    def _url(self, operation: str, params: dict[str, Any]) -> str:
        if not self._service_key:
            raise ProviderError("KECO", "환경공단 API 키가 설정되지 않았습니다.")
        # Keep already URL-encoded '%' intact while also supporting the decoded key form.
        service_key = quote(self._service_key, safe="%")
        return f"{KECO_BASE_URL}/{operation}?{urlencode(params)}&serviceKey={service_key}"

    def _get_page(self, operation: str, *, page_no: int, num_rows: int, extra: dict[str, Any]) -> dict[str, Any]:
        params = {"pageNo": page_no, "numOfRows": num_rows, "dataType": "JSON", **extra}
        request = Request(self._url(operation, params), headers={"Accept": "application/json", "User-Agent": "ChargePin/1.0"})
        try:
            with urlopen(request, timeout=12) as response:
                body = response.read().decode("utf-8")
        except HTTPError as error:
            if error.code in (401, 403):
                raise ProviderError("KECO", "환경공단 API 인증 또는 활용 신청 상태를 확인해 주세요.") from error
            if error.code == 429:
                raise ProviderError("KECO", "환경공단 API 요청이 제한되었습니다. 잠시 후 다시 시도해 주세요.", retryable=True) from error
            raise ProviderError("KECO", "환경공단 API를 호출하지 못했습니다.", retryable=True) from error
        except (URLError, TimeoutError) as error:
            raise ProviderError("KECO", "환경공단 응답이 지연되고 있습니다.", retryable=True) from error
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            try:
                root = ElementTree.fromstring(body)
                message = root.findtext(".//resultMsg") or "환경공단 API 응답 형식을 확인할 수 없습니다."
            except ElementTree.ParseError:
                message = "환경공단 API 응답 형식을 확인할 수 없습니다."
            raise ProviderError("KECO", message)
        code = str(payload.get("resultCode", ""))
        message = str(payload.get("resultMsg", ""))
        if (code and code != "00") or (message and "NORMAL" not in message.upper() and "OK" not in message.upper()):
            raise ProviderError("KECO", "환경공단 API 요청이 거부되었습니다. 인증키와 활용 신청 상태를 확인해 주세요.")
        return payload

    def _all_pages(self, operation: str, extra: dict[str, Any]) -> list[dict[str, Any]]:
        first = self._get_page(operation, page_no=1, num_rows=9999, extra=extra)
        items = as_items(first)
        try:
            total = int(first.get("totalCount", len(items)))
        except (TypeError, ValueError):
            total = len(items)
        for page_no in range(2, ceil(total / 9999) + 1):
            items.extend(as_items(self._get_page(operation, page_no=page_no, num_rows=9999, extra=extra)))
        return items

    def _zscode(self, search: SearchInput) -> str | None:
        for filter_value in search.region_filters:
            text = str(filter_value)
            if text.startswith("zscode:") and text[7:] in DISTRICT_CODES.values():
                return text[7:]
            match = district_code(text)
            if match:
                return match
        return None

    def _info(self, zscode: str | None) -> list[dict[str, Any]]:
        cache_key = zscode or SEOUL_ZCODE
        now = kst_now()
        with self._lock:
            cached = self._info_cache.get(cache_key)
            if cached and now - cached[0] < timedelta(seconds=self._cache_ttl_seconds):
                return cached[1]
        filters: dict[str, Any] = {"zcode": SEOUL_ZCODE}
        if zscode:
            filters["zscode"] = zscode
        records = self._all_pages("getChargerInfo", filters)
        with self._lock:
            self._info_cache[cache_key] = (now, records)
        return records

    def _recent_statuses(self) -> dict[tuple[str, str], dict[str, Any]]:
        # The status API is a recent-update feed. It supplements info.stat/statUpdDt instead of erasing it.
        now = kst_now()
        with self._lock:
            if self._status_cache and now - self._status_cache[0] < timedelta(seconds=self._status_cache_ttl_seconds):
                return self._status_cache[1]
        records = self._all_pages("getChargerStatus", {"zcode": SEOUL_ZCODE, "period": 10})
        indexed = {(str(item.get("statId")), str(item.get("chgerId"))): item for item in records}
        with self._lock:
            self._status_cache = (now, indexed)
        return indexed

    def nearby(self, search: SearchInput) -> list[dict[str, Any]]:
        # getChargerInfo also carries the latest reported status.  Keep it usable when the
        # separate recent-update feed is temporarily slow or unavailable; Critic will mark
        # stale/missing timestamps instead of returning a misleading empty search.
        try:
            status_by_charger = self._recent_statuses()
        except ProviderError:
            status_by_charger = {}
        grouped: dict[str, dict[str, Any]] = {}
        for item in self._info(self._zscode(search)):
            if str(item.get("delYn", "N")).upper() == "Y":
                continue
            try:
                latitude, longitude = float(item["lat"]), float(item["lng"])
            except (KeyError, TypeError, ValueError):
                continue
            distance = distance_km(search.center, latitude, longitude)
            if distance > search.radius_km:
                continue
            kind = connector_type(item.get("chgerType"))
            if kind is None or kind not in search.connector_types:
                continue
            station_id, charger_id = str(item.get("statId") or ""), str(item.get("chgerId") or "")
            if not station_id or not charger_id:
                continue
            status = status_by_charger.get((station_id, charger_id), item)
            station = grouped.setdefault(station_id, {
                "stat_id": station_id, "name": str(item.get("statNm") or "충전소명 확인 필요"),
                "address": str(item.get("addr") or item.get("location") or "주소 확인 필요"), "lat": latitude, "lng": longitude,
                "kind": facility_type(item), "use_time": str(item.get("useTime") or "") or None,
                "parking_free": {"Y": True, "N": False}.get(str(item.get("parkingFree", "")).upper()),
                "restriction_detail": str(item.get("limitDetail") or "") or None, "chargers": [], "distance_km": round(distance, 2),
            })
            station["chargers"].append((charger_id, kind, str(status.get("stat") or "9"), parse_keco_time(status.get("statUpdDt"))))
        now = kst_now()
        for station in grouped.values():
            station["fetched_at"] = now
        return sorted(grouped.values(), key=lambda item: item["distance_km"])
