import unittest

from app.agents import SearchOrchestrator
from app.models import ConfirmInput, ConnectorType, PlaceCandidate, Point, SearchInput
from app.providers import kst_now


class SearchOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SearchOrchestrator()
        self.service.executor._chargers.nearby = lambda _search: [{
            "stat_id": "test-station", "name": "테스트 충전소", "address": "서울특별시 강남구 테스트로 1",
            "lat": 37.498, "lng": 127.027, "kind": "시설 유형 확인 필요", "use_time": "24시간",
            "parking_free": None, "restriction_detail": None, "distance_km": 0.1, "fetched_at": kst_now(),
            "chargers": [("01", ConnectorType.FAST, "2", kst_now()), ("02", ConnectorType.SLOW, "3", kst_now())],
        }]
        self.service.executor._places.top_two = lambda _query: [
            PlaceCandidate(candidate_id="city-hall", name="서울특별시청", category="공공기관", address="서울특별시 중구 세종대로 110", location=Point(lat=37.5665, lng=126.9780, source="kakao_candidate"), district_code="11140"),
            PlaceCandidate(candidate_id="seoul-station", name="서울역", category="기차역", address="서울특별시 용산구 한강대로 405", location=Point(lat=37.5550, lng=126.9710, source="kakao_candidate"), district_code="11170"),
        ]

    def test_default_search_is_gangnam_three_km_with_both_types(self) -> None:
        response = self.service.default_search("GUEST")
        self.assertEqual(response.applied_request.origin.value, "initial_default")
        self.assertEqual(response.applied_request.radius_km, 3)
        self.assertEqual(set(response.applied_request.connector_types), {ConnectorType.FAST, ConnectorType.SLOW})
        self.assertTrue(response.results)

    def test_bare_seoul_returns_two_candidates_before_charger_state_search(self) -> None:
        plan = self.service.plan_chat("서울", "GUEST")
        self.assertEqual(plan.status, "AWAITING_LOCATION_CONFIRMATION")
        self.assertEqual(len(plan.candidates), 2)
        self.assertEqual(plan.candidates[0].name, "서울특별시청")
        response = self.service.confirm_chat(plan.request_id, ConfirmInput(candidate_id=plan.candidates[0].candidate_id), "GUEST")
        self.assertTrue(hasattr(response, "results"))

    def test_availability_never_exceeds_total(self) -> None:
        response = self.service.direct_search(SearchInput(
            center=Point(lat=37.498, lng=127.027), radius_km=3,
            connector_types=[ConnectorType.FAST, ConnectorType.SLOW],
        ), "GUEST")
        for result in response.results:
            availability = result.availability
            if availability.available_chargers is not None:
                self.assertLessEqual(availability.available_chargers, availability.total_chargers)


if __name__ == "__main__":
    unittest.main()
