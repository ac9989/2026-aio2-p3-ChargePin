"""Behavior checks for the shared preview entry and navigation."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"
if str(FRONTEND) not in sys.path:
    sys.path.insert(0, str(FRONTEND))

from streamlit.testing.v1 import AppTest


def button(app: AppTest, label: str):
    return next(item for item in app.button if item.label == label)


def enter(app: AppTest, code: str) -> AppTest:
    next(item for item in app.text_input if item.label == "접속 코드").set_value(code)
    return button(app, "입장하기").click().run()


class EntryPreviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.code_patch = patch.dict(os.environ, {"CHARGEPIN_USER_CODE": "aio2boot", "CHARGEPIN_ADMIN_CODE": "aio2"})
        self.code_patch.start()
        self.addCleanup(self.code_patch.stop)

    def assert_no_exception(self, app: AppTest) -> None:
        self.assertFalse([str(item.value) for item in app.exception])

    def test_entry_code_and_screen_round_trip(self) -> None:
        app = AppTest.from_file(str(FRONTEND / "app.py"), default_timeout=30).run()
        self.assert_no_exception(app)
        self.assertFalse(any(item.label == "검색" for item in app.button))
        enter(app, "틀린 코드")
        self.assert_no_exception(app)
        self.assertTrue(app.error)
        self.assertFalse(any(item.label == "검색" for item in app.button))
        enter(app, "AIO2")
        self.assert_no_exception(app)
        button(app, "검색").click().run()
        self.assert_no_exception(app)
        self.assertTrue(app.session_state["search_complete"])
        button(app, "관리자 대시보드").click().run()
        self.assert_no_exception(app)
        self.assertEqual(app.session_state["active_view"], "dashboard")
        self.assertFalse(any(item.label == "접속 코드" for item in app.text_input))
        app.radio[0].set_value("서비스 운영").run()
        self.assert_no_exception(app)
        self.assertTrue(any("quality-bar" in item.value for item in app.markdown))
        self.assertTrue(any("guard-track" in item.value for item in app.markdown))
        self.assertTrue(any(item.label == "예시 요청 재처리" for item in app.button))
        button(app, "← 사용자 화면").click().run()
        self.assert_no_exception(app)
        self.assertTrue(app.session_state["search_complete"])
        self.assertTrue(any(item.label == "조건 변경" for item in app.button))

    def test_search_modes_and_compact_results(self) -> None:
        app = AppTest.from_file(str(FRONTEND / "app.py"), default_timeout=30).run()
        enter(app, "aio2boot")
        self.assert_no_exception(app)
        self.assertFalse(any(item.label == "검색 대상" for item in app.radio))
        mode = next(item for item in app.radio if item.label == "검색 방식")
        mode.set_value("AI 챗").run()
        self.assertTrue(app.chat_input)
        self.assertFalse(any(item.label == "검색" for item in app.button))
        app.chat_input[0].set_value("강남").run()
        self.assert_no_exception(app)
        self.assertTrue(app.session_state["search_complete"])
        self.assertEqual(app.session_state["search_mode"], "AI 챗")
        self.assertEqual(app.session_state["last_criteria"].connector_type, "급속")
        self.assertTrue(any("강남역 기준" in str(item.value) and "완속" in str(item.value) for item in app.markdown))
        self.assertTrue(app.session_state["result_list"])
        next(item for item in app.radio if item.label == "검색 방식").set_value("탐색").run()
        self.assert_no_exception(app)
        self.assertTrue(any(item.label == "조건 변경" for item in app.button))
        self.assertTrue(any("장소 유형" in item.value and "주차 요금" in item.value and "외부인 이용" in item.value for item in app.markdown))
        button(app, "조건 변경").click().run()
        self.assert_no_exception(app)
        self.assertTrue(any(item.label == "검색" for item in app.button))
        self.assertTrue(any(item.label == "결과로 돌아가기" for item in app.button))

    def test_chat_seoul_and_follow_up_show_places(self) -> None:
        app = AppTest.from_file(str(FRONTEND / "app.py"), default_timeout=30).run()
        enter(app, "aio2boot")
        next(item for item in app.radio if item.label == "검색 방식").set_value("AI 챗").run()
        app.chat_input[0].set_value("서울").run()
        self.assert_no_exception(app)
        self.assertTrue(any("서울시청 기준" in str(item.value) and "예시 서울역 주변 충전소" in str(item.value) for item in app.markdown))
        self.assertTrue(all(item.get("charger_type") == "급속" for item in app.session_state["result_list"]))
        app.chat_input[0].set_value("네").run()
        self.assert_no_exception(app)
        self.assertEqual(app.session_state["last_criteria"].connector_type, "전체")
        self.assertTrue(any(item.get("charger_type") == "완속" for item in app.session_state["result_list"]))

    def test_extra_filters_apply_only_to_confirmed_information(self) -> None:
        app = AppTest.from_file(str(FRONTEND / "app.py"), default_timeout=30).run()
        enter(app, "aio2boot")
        next(item for item in app.radio if item.label == "주차 요금").set_value("무료").run()
        next(item for item in app.radio if item.label == "외부인 이용").set_value("가능").run()
        next(item for item in app.radio if item.label == "주차 현황").set_value("자리 있음").run()
        button(app, "검색").click().run()
        self.assert_no_exception(app)
        self.assertEqual(app.session_state["last_criteria"].parking_fee, "무료")
        self.assertEqual(app.session_state["last_criteria"].access, "가능")
        self.assertEqual(app.session_state["last_criteria"].parking_occupancy, "자리 있음")
        self.assertEqual([item["id"] for item in app.session_state["result_list"]], ["example-charger-3"])

    def test_preview_errors_disable_and_restore_inputs(self) -> None:
        app = AppTest.from_file(str(FRONTEND / "app.py"), default_timeout=30).run()
        enter(app, "aio2boot")
        preview = lambda: next(item for item in app.radio if item.label == "시연할 상황")

        preview().set_value("AI 챗 연결 실패").run()
        self.assert_no_exception(app)
        self.assertEqual(app.session_state["search_mode"], "AI 챗")
        self.assertTrue(app.chat_input[0].disabled)
        self.assertTrue(any("[시연]" in str(item.value) for item in app.warning))

        preview().set_value("시연 해제").run()
        self.assert_no_exception(app)
        self.assertFalse(app.chat_input[0].disabled)
        app.chat_input[0].set_value("강남역 3 km 급속 충전 장소").run()
        self.assertTrue(app.session_state["search_complete"])

        for state in ("요청 제한", "인증 만료", "권한 없음"):
            preview().set_value(state).run()
            self.assert_no_exception(app)
            self.assertTrue(app.chat_input[0].disabled)

        next(item for item in app.radio if item.label == "검색 방식").set_value("탐색").run()
        if any(item.label == "조건 변경" for item in app.button):
            button(app, "조건 변경").click().run()
        self.assertTrue(button(app, "검색").disabled)
        preview().set_value("시연 해제").run()
        self.assert_no_exception(app)
        self.assertFalse(button(app, "검색").disabled)

    def test_empty_result_preview_preserves_previous_results(self) -> None:
        app = AppTest.from_file(str(FRONTEND / "app.py"), default_timeout=30).run()
        enter(app, "aio2boot")
        button(app, "검색").click().run()
        result_count = len(app.session_state["result_list"])
        self.assertGreater(result_count, 0)

        preview = lambda: next(item for item in app.radio if item.label == "시연할 상황")
        preview().set_value("결과 없음").run()
        self.assert_no_exception(app)
        self.assertEqual(len(app.session_state["result_list"]), result_count)
        self.assertTrue(any("[시연]" in str(item.value) for item in app.info))
        self.assertFalse(any(item.label == "예시 전용 충전소" for item in app.button))

        preview().set_value("시연 해제").run()
        self.assert_no_exception(app)
        self.assertEqual(len(app.session_state["result_list"]), result_count)
        self.assertTrue(any(item.label == "예시 전용 충전소" for item in app.button))

    def test_general_user_cannot_open_dashboard_and_can_sign_out(self) -> None:
        app = AppTest.from_file(str(FRONTEND / "app.py"), default_timeout=30).run()
        enter(app, "AIO2BOOT")
        self.assert_no_exception(app)
        self.assertEqual(app.session_state["entry_role"], "user")
        self.assertTrue(any(item.label == "검색" for item in app.button))
        self.assertFalse(any(item.label == "관리자 대시보드" for item in app.button))
        app.session_state["active_view"] = "dashboard"
        app.run()
        self.assert_no_exception(app)
        self.assertTrue(any("관리자 권한" in str(item.value) for item in app.error))
        self.assertFalse(any(item.value == "운영 개요" for item in app.title))
        button(app, "사용자 화면으로 돌아가기").click().run()
        self.assert_no_exception(app)
        button(app, "⏻").click().run()
        self.assert_no_exception(app)
        self.assertTrue(any(item.label == "접속 코드" for item in app.text_input))
        self.assertFalse(any(item.label == "검색" for item in app.button))

    def test_identical_role_codes_are_rejected(self) -> None:
        with patch.dict(os.environ, {"CHARGEPIN_USER_CODE": "same", "CHARGEPIN_ADMIN_CODE": "same"}):
            app = AppTest.from_file(str(FRONTEND / "app.py"), default_timeout=30).run()
            enter(app, "same")
            self.assert_no_exception(app)
            self.assertTrue(any("접속 코드 설정" in str(item.value) for item in app.error))
            self.assertFalse(any(item.label == "검색" for item in app.button))

    def test_dashboard_launcher_uses_same_entry_flow(self) -> None:
        app = AppTest.from_file(str(FRONTEND / "dashboard" / "app.py"), default_timeout=30).run()
        self.assert_no_exception(app)
        enter(app, "aio2")
        self.assert_no_exception(app)
        self.assertTrue(any(item.label == "검색" for item in app.button))
        button(app, "관리자 대시보드").click().run()
        self.assert_no_exception(app)
        self.assertTrue(any(item.label == "← 사용자 화면" for item in app.button))


if __name__ == "__main__":
    unittest.main()