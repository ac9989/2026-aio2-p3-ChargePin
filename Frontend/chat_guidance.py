"""Truthful, short summaries and follow-ups for observed charger results."""
from __future__ import annotations

import math
import re
from typing import Any


def parking_mode_for_message(message: str) -> str:
    text = re.sub(r"\s+", "", message)
    if re.search(r"유료주차|주차.{0,3}유료|무료주차.{0,3}아닌", text):
        return "무료 아님"
    if re.search(r"무료주차|주차.{0,3}무료", text):
        return "무료"
    conditions = ("급속", "완속", "유료", "무료", "주차", "가능", "이용", "시간", "요금", "아파트", "충전소", "밖에", "반경", "거리", "km", "미터")
    return "전체" if any(word in text.lower() for word in conditions) else "무료"


def followup_mode(message: str) -> str | None:
    text = re.sub(r"[\s?!.,~]+", "", message)
    tail = r"(?:도|만|좀)?(?:보여줘|보여주세요|찾아줘|찾아주세요|알려줘|알려주세요|볼래|보고싶어|볼수있어|있어)?"
    if re.fullmatch(r"(?:유료|유료주차|유료충전소|무료주차아닌곳|무료아닌곳|무료가아닌곳)" + tail, text):
        return "무료 아님"
    if re.fullmatch(r"(?:무료|무료주차|무료충전소|무료주차인곳)" + tail, text):
        return "무료"
    if re.fullmatch(r"(?:전체|모두|전부|모든곳)" + tail, text):
        return "전체"
    if re.fullmatch(r"(?:요금확인필요|주차요금확인필요|주차확인필요|확인필요한곳)" + tail, text):
        return "확인 필요"
    return None



def unapplied_conditions(message: str) -> list[str]:
    text = re.sub(r"\s+", "", message)
    conditions = []
    if re.search(r"24시간|24시|이용시간|운영시간|심야|야간|주말", text):
        conditions.append("이용 시간")
    if re.search(r"외부인|일반인|출입|개방", text):
        conditions.append("외부인 이용")
    return conditions


def select_parking(results: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    if mode == "무료":
        return [item for item in results if item.get("parking_free") is True]
    if mode == "무료 아님":
        return [item for item in results if item.get("parking_free") is False]
    if mode == "확인 필요":
        return [item for item in results if item.get("parking_free") is None]
    return list(results)


def has_map_location(item: dict[str, Any]) -> bool:
    try:
        location = item.get("location") or {}
        latitude, longitude = float(location["lat"]), float(location["lng"])
        return math.isfinite(latitude) and math.isfinite(longitude) and -90 <= latitude <= 90 and -180 <= longitude <= 180
    except (KeyError, TypeError, ValueError):
        return False


def safe_markdown(value: Any) -> str:
    text = " ".join(str(value or "").split())
    return re.sub(r"([\\`*_{}\[\]()<>#+.!|~-])", r"\\\1", text)


def guidance(results: list[dict[str, Any]], location: str, mode: str, radius: Any,
             status: str = "completed", unapplied: list[str] | None = None) -> tuple[str, list[tuple[str, str]]]:
    selected = select_parking(results, mode)
    label = {"무료": "무료 주차가 확인된 충전소", "무료 아님": "무료 주차가 아닌 충전소",
             "확인 필요": "주차 요금 확인이 필요한 충전소", "전체": "충전소"}.get(mode, "충전소")
    area = safe_markdown(location or "요청한 장소")
    search_range = radius * 2 if isinstance(radius, (int, float)) else None
    range_text = f" · 검색 범위 {search_range:g}km" if isinstance(search_range, (int, float)) else ""
    message = f"**{area} 주변{range_text}**\n\n"
    if selected:
        message += f"{label} **{len(selected):,}곳**을 찾았어요."
        for item in selected[:2]:
            name = safe_markdown(item.get("name") or "이름 확인 필요")
            facility = safe_markdown(item.get("facility_type") or "시설 유형 확인 필요")
            message += f"\n- {name} · {facility}"
    else:
        message += f"현재 응답에서 {label}를 찾지 못했어요."
    missing = sum(not has_map_location(item) for item in selected)
    if missing:
        message += f"\n\n위치 정보가 없는 {missing:,}곳은 지도에 표시할 수 없어요."
    elif selected:
        message += "\n\n지도에서 충전소를 선택하면 상세 정보를 볼 수 있어요."
    if unapplied:
        message += "\n\n" + " · ".join(unapplied) + " 조건은 아직 자동으로 걸러지지 않았어요."
    if status == "degraded":
        message += "\n\n일부 정보는 확인이 어려워요. 지도 위 안내를 확인해 주세요."
    options = []
    if mode != "무료" and select_parking(results, "무료"):
        options.append(("무료 주차 보기", "무료"))
    if mode != "무료 아님" and select_parking(results, "무료 아님"):
        options.append(("무료 주차 아닌 곳 보기", "무료 아님"))
    if mode != "확인 필요" and select_parking(results, "확인 필요"):
        options.append(("주차 요금 확인 필요 보기", "확인 필요"))
    if mode != "전체" and len(results) > len(selected):
        options.append(("전체 보기", "전체"))
    if options:
        message += "\n\n다른 주차 조건도 볼까요?"
    message += "\n\n주차 요금과 충전 요금은 별도이며, 충전 요금은 확인할 수 없어요."
    return message, options
