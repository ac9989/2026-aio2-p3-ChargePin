"""Tests for search inputs and safe availability presentation."""
import unittest

from services.preview import (
    SearchCriteria, DEFAULT_CENTER, CITY_HALL_CENTER, safe_card, site_information,
    marker_information, usage_limit_label, PreviewProvider, parse_preview_query,
)


class PreviewDataTests(unittest.TestCase):
    def test_rejects_unsupported_radius(self):
        with self.assertRaises(ValueError):
            SearchCriteria(radius=10).confirm()

    def test_delayed_result_hides_counts(self):
        card = safe_card({
            'kind': "주차장", 'status': "DELAYED", 'total_spaces': 50,
            'current_vehicles': 38, 'available_spaces': 12, 'chargers': [("1", "사용 가능")],
        })
        for field in ('total_spaces', 'current_vehicles', 'available_spaces', 'chargers'):
            self.assertNotIn(field, card)

    def test_missing_report_time_hides_availability(self):
        card = safe_card({
            'kind': "주차장", 'status': "AVAILABLE", 'total_spaces': 50, 'current_vehicles': 38,
        })
        self.assertEqual(card['status'], "UNAVAILABLE")
        self.assertNotIn("available_spaces", card)

    def test_invalid_parking_count_is_unavailable(self):
        card = safe_card({
            'kind': "주차장", 'status': "AVAILABLE", 'reported_at': "예시",
            'total_spaces': 50, 'current_vehicles': 51,
        })
        self.assertEqual(card['status'], "UNAVAILABLE")
        self.assertNotIn("available_spaces", card)

    def test_search_only_returns_charging_places_or_candidates(self):
        results = PreviewProvider().search(SearchCriteria())
        self.assertTrue(results)
        self.assertTrue(all(facility['kind'] in ("충전소", "후보") for facility in results))

    def test_missing_or_unrecognized_site_information_is_unknown(self):
        info = site_information({"site_type": ["UNRECOGNIZED"], "parking_fee": None, "access": "UNKNOWN"})
        self.assertEqual(info["site_type"], "확인 필요")
        self.assertEqual(info["parking_fee"], "확인 필요")
        self.assertEqual(info["access"], "확인 필요")

    def test_site_information_distinguishes_parking_fee_and_access(self):
        info = site_information({"site_type": "APARTMENT", "parking_fee": "PAID", "access": "RESTRICTED", "access_detail": "입주민 전용"})
        self.assertEqual(info["site_type"], "아파트")
        self.assertEqual(info["parking_fee"], "유료")
        self.assertEqual(info["access"], "주의")
        self.assertEqual(info["access_detail"], "입주민 전용")

    def test_empty_region_has_no_results(self):
        self.assertEqual(PreviewProvider().search(SearchCriteria(region="서초구")), [])

    def test_chat_returns_draft_before_search(self):
        results = parse_preview_query("강남역 3 km 급속 충전소와 주차장", DEFAULT_CENTER)
        self.assertIn("criteria", results)
        self.assertEqual(results['criteria'].radius, 3)
        self.assertEqual(results['criteria'].connector_type, "급속")

    def test_latest_radius_correction_is_used(self):
        results = parse_preview_query("강남역 10 km 급속 충전소 3 km", DEFAULT_CENTER)
        self.assertEqual(results['criteria'].radius, 3)

    def test_missing_charger_type_defaults_to_fast(self):
        results = parse_preview_query("강남역 3 km 충전소", DEFAULT_CENTER)
        self.assertEqual(results["criteria"].connector_type, "급속")

    def test_broad_location_uses_an_explicit_representative_center(self):
        seoul = parse_preview_query("서울", DEFAULT_CENTER)
        gangnam = parse_preview_query("강남", CITY_HALL_CENTER)
        self.assertEqual((seoul["criteria"].latitude, seoul["criteria"].longitude), CITY_HALL_CENTER)
        self.assertEqual(seoul["center_label"], "서울시청")
        self.assertEqual((gangnam["criteria"].latitude, gangnam["criteria"].longitude), DEFAULT_CENTER)
        self.assertEqual(gangnam["center_label"], "강남역")

    def test_single_sentence_understands_common_parking_and_access_phrases(self):
        result = parse_preview_query(
            "강남에서 외부인도 이용할 수 있고 주차비가 안 드는 급속 충전소", DEFAULT_CENTER,
        )
        criteria = result["criteria"]
        self.assertEqual(criteria.parking_fee, "무료")
        self.assertEqual(criteria.access, "가능")
        self.assertEqual(criteria.connector_type, "급속")
        self.assertEqual([item["id"] for item in PreviewProvider().search(criteria)], ["example-charger-3"])

    def test_external_access_is_not_confused_with_time_limit(self):
        criteria = parse_preview_query(
            "강남 외부인도 이용 가능하고 이용 제한시간 1시간 이상", DEFAULT_CENTER,
        )["criteria"]
        self.assertEqual(criteria.access, "가능")
        self.assertEqual(criteria.usage_limit, "1시간 이상")

    def test_parking_free_is_not_confused_with_free_charging(self):
        criteria = parse_preview_query("강남 주차 무료 충전소", DEFAULT_CENTER)["criteria"]
        self.assertEqual(criteria.parking_fee, "무료")

    def test_duration_does_not_imply_public_access(self):
        criteria = parse_preview_query("강남에서 2시간 이상 이용 가능한 충전소", DEFAULT_CENTER)["criteria"]
        self.assertEqual(criteria.usage_limit, "2시간 이상")
        self.assertEqual(criteria.access, "전체")

    def test_ambiguous_or_unsupported_charging_price_is_not_assumed(self):
        self.assertIn("주차 요금인지", parse_preview_query("강남 무료 급속", DEFAULT_CENTER)["message"])
        self.assertIn("충전 요금", parse_preview_query("강남 충전요금 무료", DEFAULT_CENTER)["message"])

    def test_follow_up_can_include_slow_chargers(self):
        first = parse_preview_query("강남", DEFAULT_CENTER)["criteria"]
        follow_up = parse_preview_query("완속도", DEFAULT_CENTER, first)["criteria"]
        self.assertEqual(follow_up.connector_type, "전체")
        self.assertEqual((follow_up.latitude, follow_up.longitude), DEFAULT_CENTER)

    def test_accessibility_labels_and_unknowns(self):
        self.assertEqual(site_information({"access": "PUBLIC"})["access"], "가능")
        self.assertEqual(site_information({"access": "NO_PUBLIC_ACCESS"})["access"], "불가능")
        self.assertEqual(site_information({"access": "RESTRICTED"})["access"], "주의")
        self.assertEqual(site_information({})["access"], "확인 필요")

    def test_unknown_parking_and_forecasts_are_not_invented(self):
        unknown = marker_information({
            "parking_occupancy": "FULL", "parking_occupancy_current": True,
            "parking_forecast_minutes": 180, "is_preview": True,
        })
        self.assertEqual(unknown["parking_status"], "확인 필요")
        self.assertEqual(unknown["forecast"], "")
        real = marker_information({
            "parking_occupancy": "FULL", "parking_occupancy_current": True,
            "parking_reported_at": "10:00", "parking_forecast_minutes": 180,
        })
        self.assertEqual(real["parking_status"], "만차")
        self.assertEqual(real["forecast"], "")

    def test_usage_limit_requires_explicit_valid_information(self):
        self.assertEqual(usage_limit_label({"charging_limit_minutes": 90}), "1시간 30분")
        self.assertEqual(usage_limit_label({"charging_limit_minutes": True}), "확인 필요")
        self.assertEqual(usage_limit_label({"charging_limit_minutes": 60, "charging_limit_unlimited": True}), "확인 필요")
        self.assertEqual(usage_limit_label({}), "확인 필요")

    def test_access_and_parking_filters_exclude_unknown_values(self):
        results = PreviewProvider().search(SearchCriteria(
            site_type="아파트", access="불가능",
        ))
        self.assertEqual([item["id"] for item in results], ["example-charger-2"])
        results = PreviewProvider().search(SearchCriteria(
            parking_fee="무료", access="가능", parking_occupancy="자리 있음", usage_limit="2시간 이상",
        ))
        self.assertEqual([item["id"] for item in results], ["example-charger-3"])


if __name__ == "__main__":
    unittest.main()

