"""Check that chat guidance reflects the returned parking and location data."""
import unittest
from chat_guidance import followup_mode, guidance, parking_mode_for_message, select_parking, unapplied_conditions


class ChatGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            {"name": "무료 주차 장소", "facility_type": "공공시설", "parking_free": True, "location": {"lat": 37.5, "lng": 127.0}},
            {"name": "무료 아님 장소", "parking_free": False, "location": {"lat": 37.5, "lng": 127.0}},
            {"name": "미확인 장소", "parking_free": None, "location": None},
        ]

    def test_location_only_defaults_to_confirmed_free_parking(self):
        self.assertEqual(parking_mode_for_message("강남역"), "무료")
        self.assertEqual(parking_mode_for_message("63빌딩"), "무료")
        self.assertEqual(parking_mode_for_message("강남역 급속 충전소"), "전체")
        self.assertEqual(parking_mode_for_message("강남역 유료 주차"), "무료 아님")
        self.assertEqual(select_parking(self.items, "무료"), self.items[:1])

    def test_followup_does_not_intercept_new_location(self):
        self.assertEqual(followup_mode("유료도 찾아줘"), "무료 아님")
        self.assertEqual(followup_mode("무료 주차 아닌 곳도 보여줘"), "무료 아님")
        self.assertIsNone(followup_mode("홍대 유료 주차 찾아줘"))

    def test_missing_parking_and_location_are_not_claimed_as_free_or_mapped(self):
        msg, options = guidance(self.items, "강남역", "무료", 0.5)
        self.assertIn("무료 주차가 확인된 충전소", msg)
        self.assertNotIn("미확인 장소", msg)
        self.assertIn(("주차 요금 확인 필요 보기", "확인 필요"), options)
        self.assertIn(("무료 주차 아닌 곳 보기", "무료 아님"), options)
        msg, _ = guidance(self.items, "강남역", "확인 필요", 0.5)
        self.assertIn("위치 정보가 없는 1곳은 지도에 표시할 수 없어요", msg)
        self.assertIn("주차 요금과 충전 요금은 별도", msg)

    def test_unapplied_conditions_are_not_misrepresented(self):
        conditions = unapplied_conditions("강남역 24시간 외부인 이용")
        self.assertEqual(conditions, ["이용 시간", "외부인 이용"])
        msg, _ = guidance(self.items, "강남역", "전체", 0.5, unapplied=conditions)
        self.assertIn("조건은 아직 자동으로 걸러지지 않았어요", msg)
        self.assertIn("충전 요금은 확인할 수 없어요", msg)

    def test_empty_and_degraded_are_qualified(self):
        msg, _ = guidance([], "강남역", "무료", 0.5, "degraded")
        self.assertIn("현재 응답에서", msg)
        self.assertIn("일부 정보는 확인이 어려워요", msg)
        self.assertNotIn("전부 다", msg)


if __name__ == "__main__":
    unittest.main()
