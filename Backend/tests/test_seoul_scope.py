import unittest

from app.models import ConnectorType, Point, SearchInput
from app.providers import EnvironmentChargerAdapter, is_seoul_address


class SeoulScopeTests(unittest.TestCase):
    def test_address_scope_accepts_only_seoul_addresses(self) -> None:
        self.assertTrue(is_seoul_address("서울특별시 강남구 테헤란로 1"))
        self.assertTrue(is_seoul_address("서울 중구 세종대로 110"))
        self.assertFalse(is_seoul_address("경기도 용인시 처인구 포곡읍"))
        self.assertFalse(is_seoul_address("주소 확인 필요"))

    def test_environment_results_drop_non_seoul_addresses(self) -> None:
        adapter = EnvironmentChargerAdapter()
        adapter._recent_statuses = lambda: {}
        adapter._info = lambda _district: [
            {
                "statId": "seoul-station", "chgerId": "01", "statNm": "서울 충전소",
                "addr": "서울특별시 강남구 테스트로 1", "lat": "37.498", "lng": "127.027",
                "chgerType": "01", "stat": "2",
            },
            {
                "statId": "outside-station", "chgerId": "01", "statNm": "외부 충전소",
                "addr": "경기도 과천시 테스트로 1", "lat": "37.499", "lng": "127.028",
                "chgerType": "01", "stat": "2",
            },
        ]
        search = SearchInput(
            center=Point(lat=37.498, lng=127.027),
            radius_km=0.5,
            connector_types=[ConnectorType.FAST],
        )

        stations = adapter.nearby(search)

        self.assertEqual([station["stat_id"] for station in stations], ["seoul-station"])


if __name__ == "__main__":
    unittest.main()
