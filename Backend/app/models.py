"""Public contracts for the ChargePin 1.0 preview API."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ConnectorType(str, Enum):
    FAST = "FAST"
    SLOW = "SLOW"


class SearchOrigin(str, Enum):
    CHAT = "chat"
    SIDEBAR = "sidebar"
    INITIAL_DEFAULT = "initial_default"


class AvailabilityState(str, Enum):
    AVAILABLE = "AVAILABLE"
    DELAYED = "DELAYED"
    UNAVAILABLE = "UNAVAILABLE"
    CANDIDATE_ONLY = "CANDIDATE_ONLY"


class Point(BaseModel):
    lat: float = Field(ge=37.0, le=38.0)
    lng: float = Field(ge=126.5, le=127.5)
    source: str = "map"


class SearchInput(BaseModel):
    center: Point
    # The UI presents a 1/2/3 km search diameter; the provider receives its radius.
    radius_km: Literal[0.5, 1.0, 1.5] = 0.5
    connector_types: list[ConnectorType] = Field(default_factory=lambda: [ConnectorType.FAST, ConnectorType.SLOW])
    region_filters: list[str] = Field(default_factory=list)

    @field_validator("connector_types")
    @classmethod
    def connector_types_must_not_be_empty(cls, value: list[ConnectorType]) -> list[ConnectorType]:
        if not value:
            raise ValueError("충전기 타입을 하나 이상 선택해 주세요.")
        return list(dict.fromkeys(value))


class SearchRequest(SearchInput):
    request_id: str
    origin: SearchOrigin
    requested_at: datetime
    user_confirmed: bool
    intent: Literal["find_charger"] = "find_charger"
    policy_version: str = "1.0-preview"


class Availability(BaseModel):
    state: AvailabilityState
    available_chargers: int | None = Field(default=None, ge=0)
    total_chargers: int | None = Field(default=None, ge=0)
    label: str
    reason: str | None = None


class ChargerResult(BaseModel):
    facility_id: str
    name: str
    address: str
    location: Point
    distance_km: float = Field(ge=0)
    facility_type: str
    connector_types: list[ConnectorType]
    availability: Availability
    source: str = "KECO_EV"
    reported_at: datetime | None = None
    fetched_at: datetime
    use_time: str | None = None
    parking_free: bool | None = None
    restriction_detail: str | None = None


class SearchResponse(BaseModel):
    request_id: str
    status: Literal["completed", "degraded"]
    applied_request: SearchRequest
    results: list[ChargerResult]
    critic_decision: Literal["PASS", "SAFE_UNAVAILABLE"]
    critic_findings: list[str] = Field(default_factory=list)


class AuthLoginInput(BaseModel):
    service_key: str = Field(min_length=1, max_length=200)


class AuthLoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    role: Literal["GUEST", "JUNIOR_ADMIN", "SENIOR_ADMIN"]
    expires_at: datetime


class ChatPlanInput(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class PlaceSuggestInput(BaseModel):
    query: str = Field(min_length=2, max_length=100)


class PlaceCandidate(BaseModel):
    candidate_id: str
    name: str
    category: str
    address: str
    location: Point
    district_code: str | None = None


class ChatPlanResponse(BaseModel):
    request_id: str
    status: Literal["AWAITING_CONFIRMATION", "AWAITING_LOCATION_CONFIRMATION", "NEEDS_INPUT", "BLOCKED"]
    message: str
    search_request: SearchRequest | None = None
    candidates: list[PlaceCandidate] = Field(default_factory=list)
    suggested_candidate_id: str | None = None


class ConfirmInput(BaseModel):
    confirmed: bool = True
    candidate_id: str | None = None
