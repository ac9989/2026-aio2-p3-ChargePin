"""Internal UI models and a preview provider for future backend integration."""
from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
import re
from typing import Any, Protocol

SEOUL_DISTRICTS = [
    "서울 전체", "강남구", "강동구", "강북구", "강서구", "관악구", "광진구",
    "구로구", "금천구", "노원구", "도봉구", "동대문구", "동작구", "마포구",
    "서대문구", "서초구", "성동구", "성북구", "송파구", "양천구", "영등포구",
    "용산구", "은평구", "종로구", "중구", "중랑구",
]
DEFAULT_CENTER = (37.498, 127.027)
CITY_HALL_CENTER = (37.5665, 126.9780)
SEOUL_STATION_CENTER = (37.5550, 126.9710)

SITE_TYPE_CODES = {"주차장": "PARKING_LOT", "아파트": "APARTMENT", "전용 충전소": "CHARGING_STATION"}
PARKING_FEE_CODES = {"무료": "FREE", "유료": "PAID"}
ACCESS_CODES = {"가능": "PUBLIC", "불가능": "NO_PUBLIC_ACCESS", "주의": "RESTRICTED"}
OCCUPANCY_CODES = {"자리 있음": "AVAILABLE", "만차": "FULL"}
LIMIT_MINUTES = {"30분 이상": 30, "1시간 이상": 60, "2시간 이상": 120}
SITE_TYPE_OPTIONS = ("전체", *SITE_TYPE_CODES)
PARKING_FEE_OPTIONS = ("전체", *PARKING_FEE_CODES)
ACCESS_OPTIONS = ("전체", *ACCESS_CODES)
OCCUPANCY_OPTIONS = ("전체", *OCCUPANCY_CODES)
LIMIT_OPTIONS = ("전체", *LIMIT_MINUTES, "제한 없음")

VALID_STATES = {"AVAILABLE", "DELAYED", "UNAVAILABLE", "CANDIDATE_ONLY"}


@dataclass(frozen=True)
class SearchCriteria:
    """Frontend-only search criteria; not a final backend contract."""
    region: str = "서울 전체"
    latitude: float = DEFAULT_CENTER[0]
    longitude: float = DEFAULT_CENTER[1]
    connector_type: str = "전체"
    radius: int = 3
    site_type: str = "전체"
    parking_fee: str = "전체"
    access: str = "전체"
    parking_occupancy: str = "전체"
    usage_limit: str = "전체"

    def confirm(self) -> None:
        if self.region not in SEOUL_DISTRICTS:
            raise ValueError("서울 지역을 선택해 주세요.")
        if self.radius not in (1, 3, 5):
            raise ValueError("반경은 1, 3, 5 km 중에서 선택해 주세요.")
        if self.connector_type not in ("전체", "급속", "완속"):
            raise ValueError("충전기 타입을 다시 선택해 주세요.")
        if (self.site_type not in SITE_TYPE_OPTIONS or self.parking_fee not in PARKING_FEE_OPTIONS
                or self.access not in ACCESS_OPTIONS or self.parking_occupancy not in OCCUPANCY_OPTIONS
                or self.usage_limit not in LIMIT_OPTIONS):
            raise ValueError("추가 조건을 다시 선택해 주세요.")
        if not (37.0 <= self.latitude <= 38.0 and 126.5 <= self.longitude <= 127.5):
            raise ValueError("서울 주변의 검색 중심을 선택해 주세요.")


class SearchProvider(Protocol):
    """Provider interface to adapt once the backend contract is agreed."""
    def search(self, criteria: SearchCriteria) -> list[dict[str, Any]]: ...


# These locations and values are synthetic preview data.
_SAMPLE_FACILITIES: list[dict[str, Any]] = [
    {
        "id": "example-parking-1", 'name': "예시 공영주차장", 'kind': "주차장",
        'region': "강남구", 'address': "서울특별시 강남구 예시로 12",
        'latitude': 37.4992, 'longitude': 127.0250, 'status': "AVAILABLE",
        'source': "서울시 시영주차장", 'reported_at': "예시 10:00",
        'fetched_at': "예시 10:00:03", 'total_spaces': 50, 'current_vehicles': 38,
    },
    {
        "id": "example-charger-1", 'name': "예시 주차장 충전기", 'kind': "충전소",
        'site_type': "PARKING_LOT", 'parking_fee': "PAID", 'access': "PUBLIC",
        'region': "강남구", 'address': "서울특별시 강남구 예시로 23",
        'latitude': 37.5004, 'longitude': 127.0297, 'status': "AVAILABLE",
        'source': "환경공단", 'reported_at': "예시 10:00", 'fetched_at': "예시 10:00:02",
        'chargers': [("급속 충전기 1", "사용 가능"), ("급속 충전기 2", "충전 중")],
        'charger_type': "급속", 'charging_limit_minutes': 60,
        'parking_occupancy': "FULL", 'parking_reported_at': "예시 10:00",
        'parking_occupancy_current': True, 'parking_forecast_minutes': 180,
    },
    {
        "id": "example-charger-2", 'name': "예시 아파트 충전기", 'kind': "충전소",
        'site_type': "APARTMENT", 'parking_fee': "UNKNOWN", 'access': "NO_PUBLIC_ACCESS", 'access_detail': "외부인 출입 불가 · 입주민 전용",
        'region': "강남구", 'address': "서울특별시 강남구 예시로 36",
        'latitude': 37.4965, 'longitude': 127.0304, 'status': "DELAYED",
        'source': "환경공단", 'reported_at': "예시 09:12", 'fetched_at': "예시 10:00",
        'reason': "마지막 보고 이후 시간이 지나 현재 상태를 확인할 수 없어요.",
        'charger_type': "완속",
    },
    {
        "id": "example-charger-3", 'name': "예시 전용 충전소", 'kind': "충전소",
        'site_type': "CHARGING_STATION", 'parking_fee': "FREE", 'access': "PUBLIC",
        'region': "강남구", 'address': "서울특별시 강남구 예시로 40",
        'latitude': 37.4971, 'longitude': 127.0238, 'status': "AVAILABLE",
        'source': "환경공단", 'reported_at': "예시 10:00", 'fetched_at': "예시 10:00:03",
        'chargers': [("급속 충전기 1", "사용 가능")], 'charger_type': "급속",
        'charging_limit_minutes': 120, 'parking_occupancy': "AVAILABLE",
        'parking_reported_at': "예시 10:00", 'parking_occupancy_current': True,
    },
    {
        "id": "example-candidate-1", 'name': "예시 장소 후보", 'kind': "후보",
        'region': "강남구", 'address': "서울특별시 강남구 예시로 45",
        'latitude': 37.4958, 'longitude': 127.0245, 'status': "CANDIDATE_ONLY",
        'source': "카카오 장소 후보", 'reported_at': "", 'fetched_at': "예시 10:00:01",
        'reason': "실시간 충전·주차 상태 정보가 없어요.", 'candidate_target': "충전소",
    },
    {
        "id": "example-parking-2", 'name': "예시 시영주차장 B", 'kind': "주차장",
        'region': "강남구", 'address': "서울특별시 강남구 예시로 56",
        'latitude': 37.5013, 'longitude': 127.0242, 'status': "UNAVAILABLE",
        'source': "서울시 시영주차장", 'reported_at': "예시 10:00", 'fetched_at': "예시 10:00:04",
        'reason': "제공된 수치를 확인할 수 없어 빈자리를 표시하지 않아요.",
    },
    {
        "id": "example-cityhall-fast", "name": "예시 시청 주변 충전소", "kind": "충전소",
        "site_type": "PARKING_LOT", "parking_fee": "PAID", "access": "PUBLIC",
        "region": "중구", "address": "서울시청 주변 예시 위치",
        "latitude": 37.5673, "longitude": 126.9800, "status": "AVAILABLE",
        "source": "시연 데이터", "reported_at": "예시 10:00", "fetched_at": "예시 10:00",
        "chargers": [("급속 충전기", "사용 가능")], "charger_type": "급속",
        "charging_limit_minutes": 60, "parking_occupancy": "AVAILABLE",
        "parking_reported_at": "예시 10:00", "parking_occupancy_current": True,
    },
    {
        "id": "example-seoul-station-fast", "name": "예시 서울역 주변 충전소", "kind": "충전소",
        "site_type": "CHARGING_STATION", "parking_fee": "FREE", "access": "RESTRICTED",
        "access_detail": "운영 시간과 출입 조건 확인 필요",
        "region": "중구", "address": "서울역 주변 예시 위치",
        "latitude": 37.5557, "longitude": 126.9720, "status": "AVAILABLE",
        "source": "시연 데이터", "reported_at": "예시 10:00", "fetched_at": "예시 10:00",
        "chargers": [("급속 충전기", "충전 중")], "charger_type": "급속",
        "charging_limit_minutes": 90, "parking_occupancy": "FULL",
        "parking_reported_at": "예시 10:00", "parking_occupancy_current": True,
        "parking_forecast_minutes": 180,
    },
    {
        "id": "example-cityhall-slow", "name": "예시 시청 주변 완속 충전기", "kind": "충전소",
        "site_type": "PARKING_LOT", "parking_fee": "PAID", "access": "PUBLIC",
        "region": "중구", "address": "서울시청 주변 예시 위치",
        "latitude": 37.5680, "longitude": 126.9774, "status": "AVAILABLE",
        "source": "시연 데이터", "reported_at": "예시 10:00", "fetched_at": "예시 10:00",
        "chargers": [("완속 충전기", "사용 가능")], "charger_type": "완속",
        "charging_limit_minutes": 240, "parking_occupancy": "AVAILABLE",
        "parking_reported_at": "예시 10:00", "parking_occupancy_current": True,
    },
]


def site_information(facility: dict[str, Any]) -> dict[str, str]:
    """Display only explicit preview attributes; missing or unknown values stay unknown."""
    types = {"PARKING_LOT": "주차장", "APARTMENT": "아파트", "CHARGING_STATION": "전용 충전소"}
    fees = {"FREE": "무료", "PAID": "유료"}
    access = {"PUBLIC": "가능", "NO_PUBLIC_ACCESS": "불가능", "RESTRICTED": "주의"}
    def label(mapping: dict[str, str], value: Any) -> str:
        return mapping.get(value, "확인 필요") if isinstance(value, str) else "확인 필요"

    access_code = facility.get("access")
    detail = facility.get("access_detail", "") if access_code in ("RESTRICTED", "NO_PUBLIC_ACCESS") else ""
    return {
        "site_type": label(types, facility.get("site_type")),
        "parking_fee": label(fees, facility.get("parking_fee")),
        "access": label(access, access_code),
        "access_detail": detail if isinstance(detail, str) else "",
    }



def parking_occupancy_code(facility: dict[str, Any]) -> str | None:
    """Return only an explicitly current parking observation with a reporting time."""
    code = facility.get("parking_occupancy")
    reported = facility.get("parking_reported_at")
    if (isinstance(code, str) and code in OCCUPANCY_CODES.values()
            and isinstance(reported, str) and bool(reported.strip())
            and facility.get("parking_occupancy_current") is True):
        return code
    return None


def usage_limit_label(facility: dict[str, Any]) -> str:
    minutes = facility.get("charging_limit_minutes")
    unlimited = facility.get("charging_limit_unlimited") is True
    if unlimited and minutes is None:
        return "제한 없음"
    if unlimited or not isinstance(minutes, int) or isinstance(minutes, bool) or not 0 < minutes <= 1440:
        return "확인 필요"
    hours, remainder = divmod(minutes, 60)
    return " ".join(part for part in (f"{hours}시간" if hours else "", f"{remainder}분" if remainder else "") if part)


def marker_information(facility: dict[str, Any]) -> dict[str, str]:
    """Prepare conservative, explicitly labelled details for map markers."""
    info = site_information(facility)
    occupancy = parking_occupancy_code(facility)
    occupancy_labels = {"AVAILABLE": "자리 있음", "FULL": "만차"}
    charger_type = facility.get("charger_type")
    if charger_type not in ("급속", "완속"):
        charger_type = "확인 필요"
    forecast = ""
    minutes = facility.get("parking_forecast_minutes")
    if (facility.get("is_preview") is True and occupancy == "FULL"
            and isinstance(minutes, int) and not isinstance(minutes, bool) and 0 < minutes <= 1440):
        hours, remainder = divmod(minutes, 60)
        duration = (f"{hours}시간 " if hours else "") + (f"{remainder}분" if remainder else "")
        forecast = f"시연 예시 · 약 {duration.strip()} 뒤 자리 생길 가능성"
    return {
        "site_type": info["site_type"], "parking_fee": info["parking_fee"],
        "access": info["access"], "access_detail": info["access_detail"],
        "charger_type": charger_type, "usage_limit": usage_limit_label(facility),
        "parking_status": occupancy_labels.get(occupancy, "확인 필요"), "forecast": forecast,
    }


def distance_km(latitude1: float, longitude1: float, latitude2: float, longitude2: float) -> float:
    """Approximate straight-line distance between two coordinates."""
    a = sin(radians(latitude2 - latitude1) / 2) ** 2
    a += cos(radians(latitude1)) * cos(radians(latitude2)) * sin(radians(longitude2 - longitude1) / 2) ** 2
    return 6371.0 * 2 * asin(min(1.0, sqrt(a)))


def safe_card(facility: dict[str, Any]) -> dict[str, Any]:
    """Remove unverified counts and charger states before displaying a result."""
    card = dict(facility)
    status = card.get('status')
    if status not in VALID_STATES:
        card['status'] = "UNAVAILABLE"
        card['reason'] = "상태 정보를 확인할 수 없어요."
    if card['status'] == "AVAILABLE" and not card.get('reported_at'):
        card['status'] = "UNAVAILABLE"
        card['reason'] = "보고 시각을 확인할 수 없어 상태를 표시하지 않아요."
    if card['status'] == "AVAILABLE" and card.get('kind') == "충전소" and not card.get('chargers'):
        card['status'] = "UNAVAILABLE"
        card['reason'] = "충전기 상태를 확인할 수 없어요."
    if card['status'] == "AVAILABLE" and card.get('kind') == "주차장":
        total_spaces, current_vehicles = card.get('total_spaces'), card.get('current_vehicles')
        if not (isinstance(total_spaces, int) and not isinstance(total_spaces, bool)
                and isinstance(current_vehicles, int) and not isinstance(current_vehicles, bool)
                and total_spaces > 0 and 0 <= current_vehicles <= total_spaces):
            card['status'] = "UNAVAILABLE"
            card['reason'] = "제공된 수치를 확인할 수 없어 빈자리를 표시하지 않아요."
    if card['status'] != "AVAILABLE":
        for name in ('total_spaces', 'current_vehicles', 'available_spaces', 'chargers'):
            card.pop(name, None)
    elif card.get('kind') == "주차장":
        card['available_spaces'] = card['total_spaces'] - card['current_vehicles']
    return card


class PreviewProvider:
    """Preview data source that makes no external API requests."""
    def search(self, criteria: SearchCriteria) -> list[dict[str, Any]]:
        criteria.confirm()
        results = []
        for record in _SAMPLE_FACILITIES:
            if criteria.region != "서울 전체" and record['region'] != criteria.region:
                continue
            kind = record['kind'] if record['kind'] != "후보" else record.get('candidate_target')
            if kind != "충전소":
                continue
            if criteria.connector_type != "전체" and record.get('charger_type') != criteria.connector_type:
                continue
            if criteria.site_type != "전체" and record.get("site_type") != SITE_TYPE_CODES[criteria.site_type]:
                continue
            if criteria.parking_fee != "전체" and record.get("parking_fee") != PARKING_FEE_CODES[criteria.parking_fee]:
                continue
            if criteria.access != "전체" and record.get("access") != ACCESS_CODES[criteria.access]:
                continue
            if criteria.parking_occupancy != "전체" and parking_occupancy_code(record) != OCCUPANCY_CODES[criteria.parking_occupancy]:
                continue
            if criteria.usage_limit != "전체":
                minutes = record.get("charging_limit_minutes")
                unlimited = record.get("charging_limit_unlimited") is True and minutes is None
                if record.get("charging_limit_unlimited") is True and minutes is not None:
                    continue
                if criteria.usage_limit == "제한 없음":
                    if not unlimited:
                        continue
                elif not unlimited and not (
                    isinstance(minutes, int) and not isinstance(minutes, bool)
                    and LIMIT_MINUTES[criteria.usage_limit] <= minutes <= 1440
                ):
                    continue
            distance = distance_km(criteria.latitude, criteria.longitude, record['latitude'], record['longitude'])
            if distance <= criteria.radius:
                card = safe_card(record)
                card["is_preview"] = True
                card['distance_km'] = distance
                results.append(card)
        return sorted(results, key=lambda card: card['distance_km'])


def parse_preview_query(
    text: str, center: tuple[float, float], previous: SearchCriteria | None = None
) -> dict[str, Any]:
    """Interpret a small set of location and filter phrases for the preview chat."""
    query = text.strip()
    if not query:
        return {"message": "찾고 싶은 지역을 말씀해 주세요."}
    if re.search(r"(무료|유료|주차장|아파트|급속|완속)\s*(?:말고|제외|아닌)", query):
        return {"message": "제외 조건은 아직 시연할 수 없어요. 원하는 조건을 직접 말씀해 주세요."}

    radius_matches = list(re.finditer(r"(\d+(?:\.\d+)?)\s*(?:km|킬로미터|킬로)", query, re.IGNORECASE))
    radius = previous.radius if previous else 3
    if radius_matches:
        value = float(radius_matches[-1].group(1))
        if value not in (1.0, 3.0, 5.0):
            return {"message": "반경은 1·3·5 km 중에서 골라 주세요."}
        radius = int(value)

    aliases = {
        "서울시청": ("서울 전체", CITY_HALL_CENTER, "서울시청"),
        "중구": ("중구", CITY_HALL_CENTER, "서울시청"),
        "서울역": ("서울 전체", SEOUL_STATION_CENTER, "서울역"),
        "강남역": ("강남구", DEFAULT_CENTER, "강남역"),
        "강남구": ("강남구", DEFAULT_CENTER, "강남역"),
        "강남": ("강남구", DEFAULT_CENTER, "강남역"),
        "시청": ("서울 전체", CITY_HALL_CENTER, "서울시청"),
        "서울": ("서울 전체", CITY_HALL_CENTER, "서울시청"),
    }
    landmark_matches = list(re.finditer(r"서울시청|서울역|강남역|강남구|강남|중구|시청|서울", query))
    other_regions = [(query.rfind(district), district) for district in SEOUL_DISTRICTS[1:]
                     if district not in ("강남구", "중구") and district in query]
    latest_other = max(other_regions, default=(-1, None))
    latest_landmark = landmark_matches[-1] if landmark_matches else None
    if latest_other[0] >= 0 and (latest_landmark is None or latest_other[0] > latest_landmark.start()):
        return {"message": f"{latest_other[1]}의 구체적인 위치를 알려 주세요. 현재 예시는 서울시청·서울역·강남역 주변을 지원해요."}

    new_location = latest_landmark is not None
    if new_location:
        region, location, center_label = aliases[latest_landmark.group(0)]
    elif previous:
        region = previous.region
        location = (previous.latitude, previous.longitude)
        center_label = (
            "서울시청" if location == CITY_HALL_CENTER else
            "서울역" if location == SEOUL_STATION_CENTER else
            "강남역" if location == DEFAULT_CENTER else "선택한 위치"
        )
    else:
        return {"message": "어느 지역을 찾으시나요? 예를 들어 서울이나 강남이라고 말씀해 주세요."}

    compact = re.sub(r"\s+", "", query)
    yes = compact.strip(".!?~") in ("응", "네", "예", "그래", "좋아", "좋아요", "네좋아요")
    no = compact.strip(".!?~") in ("아니", "아니요", "괜찮아", "괜찮아요")
    if no and previous and not new_location:
        return {"message": "지금 조건을 유지할게요. 다른 지역이나 조건도 말씀해 주세요."}

    base = previous if previous and not new_location else None
    has_fast = "급속" in query
    has_slow = "완속" in query or "완숙" in query
    if (has_fast and has_slow) or "둘 다" in query or "모두" in query or (yes and base and base.connector_type == "급속"):
        connector = "전체"
    elif has_slow:
        connector = "전체" if base and base.connector_type == "급속" and ("완속도" in compact or "완숙도" in compact or "함께" in query or "같이" in query) else "완속"
    elif has_fast:
        connector = "급속"
    else:
        connector = base.connector_type if base else "급속"

    site_type = base.site_type if base else "전체"
    fee = base.parking_fee if base else "전체"
    access = base.access if base else "전체"
    occupancy = base.parking_occupancy if base else "전체"
    limit = base.usage_limit if base else "전체"
    if "아파트" in query:
        site_type = "아파트"
    elif "주차장" in query:
        site_type = "주차장"
    elif "전용 충전소" in query:
        site_type = "전용 충전소"
    charge_price = re.search(
        r"충전(?:비|요금|료)(?:가|이|은|는)?(?:무료|유료|없|안드|안들)",
        compact,
    )
    if charge_price:
        return {"message": "충전 요금 조건은 아직 확인할 수 없어요. 주차 요금은 조건에 넣어 찾을 수 있어요."}
    if ("무료" in compact or "유료" in compact) and "주차" not in compact:
        return {"message": "무료·유료가 주차 요금인지 충전 요금인지 알려 주세요. 충전 요금은 아직 확인할 수 없어요."}

    parking_free = bool(re.search(
        r"무료주차|주차(?:비|요금|료)?(?:가|이|은|는)?(?:무료|없|안드|안들|들지않)",
        compact,
    ))
    parking_paid = bool(re.search(
        r"유료주차|주차(?:비|요금|료)?(?:가|이|은|는)?(?:유료|있|들어|드는)",
        compact,
    ))
    if parking_free and parking_paid:
        return {"message": "주차 요금은 무료와 유료 중 어느 쪽으로 찾을까요?"}
    if parking_free:
        fee = "무료"
    elif parking_paid:
        fee = "유료"

    external_mentioned = any(word in compact for word in ("외부인", "일반인", "방문객", "누구나"))
    external_denied = external_mentioned and bool(re.search(
        r"(?:외부인|일반인|방문객)(?:도|은|는|이|가|의)?(?:출입|이용|접근)?(?:할수)?(?:불가|금지|안되|못|없)",
        compact,
    ))
    external_allowed = "누구나" in compact or bool(re.search(
        r"(?:외부인|일반인|방문객)(?:도|은|는|이|가|의)?(?:출입|이용|접근|방문|들어갈|갈|쓸)?(?:할수|수)?(?:가능|있)",
        compact,
    ))
    external_conditional = external_mentioned and bool(re.search(
        r"(?:외부인|일반인|방문객)(?:도|은|는|이|가|의)?(?:출입|이용|접근)?(?:제한|주의|허가|승인)",
        compact,
    ))
    if external_denied:
        access = "불가능"
    elif external_allowed:
        access = "가능"
    elif external_conditional or "입주민전용" in compact or "입주민만" in compact:
        access = "주의"

    parking_available = bool(re.search(
        r"빈자리|자리가?있는|주차(?:자리|공간|면)(?:가|이|은|는)?(?:있|남)",
        compact,
    ))
    if parking_available:
        occupancy = "자리 있음"
    elif "만차" in compact:
        occupancy = "만차"

    limit_found = False
    for option in LIMIT_OPTIONS[1:]:
        if option.replace(" ", "") in compact:
            limit = option
            limit_found = True
    duration_match = re.search(r"(\d+)시간(?:동안|이상|넘게)(?:충전|이용|쓸|사용)?", compact)
    if duration_match and not limit_found:
        hours = int(duration_match.group(1))
        if hours in (1, 2):
            limit = f"{hours}시간 이상"
            limit_found = True
        else:
            return {"message": "이용 제한시간은 현재 30분·1시간·2시간 이상 조건으로 시연할 수 있어요."}

    touched = (
        has_fast or has_slow or bool(radius_matches) or parking_free or parking_paid
        or external_mentioned or parking_available or limit_found
        or any(value in compact for value in ("주차장", "아파트", "전용충전소", "입주민전용", "입주민만", "만차"))
    )
    if not new_location and not touched and not yes:
        return {"message": "다른 지역이나 원하는 충전 조건을 알려 주세요."}
    criteria = SearchCriteria(region, location[0], location[1], connector, radius, site_type, fee, access, occupancy, limit)
    criteria.confirm()
    return {"criteria": criteria, "center_label": center_label}
