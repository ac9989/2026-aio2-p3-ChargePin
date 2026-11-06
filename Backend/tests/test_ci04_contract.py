import ast
import unittest
from pathlib import Path

from fastapi.routing import APIRoute

from app.main import app
from app.models import SearchInput, SearchResponse


ROOT = Path(__file__).resolve().parents[2]


class ApiContractTests(unittest.TestCase):

    def test_frontend_api_paths_match_backend(self):
        """프론트엔드 API 호출 경로가 백엔드에 존재하는지 확인."""
        tree = ast.parse(
            (ROOT / "Frontend/api_client.py").read_text(encoding="utf-8-sig")
        )

        routes = {
            (route.path, method)
            for route in app.routes
            if isinstance(route, APIRoute)
            for method in route.methods
        }

        expected_methods = [
            "login",
            "default_search",
            "suggest_places",
            "search",
            "plan",
        ]

        for name in expected_methods:
            function = next(
                node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef)
                and node.name == name
            )

            calls = [
                node for node in ast.walk(function)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_request"
            ]

            self.assertEqual(len(calls), 1, name)

            method = ast.literal_eval(calls[0].args[0])
            path = ast.literal_eval(calls[0].args[1])

            self.assertIn(
                (f"/api/v1{path}", method),
                routes,
                f"API 계약 불일치: {name} → {method} {path}",
            )

    def test_search_payload_fields_match_backend(self):
        """프론트 검색 요청의 필드가 백엔드 입력 모델과 일치하는지 확인."""
        tree = ast.parse(
            (ROOT / "Frontend/app.py").read_text(encoding="utf-8-sig")
        )

        function = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "search_payload"
        )

        payload = next(
            node.value for node in ast.walk(function)
            if isinstance(node, ast.Return)
            and isinstance(node.value, ast.Dict)
        )

        frontend_fields = {
            ast.literal_eval(key) for key in payload.keys
        }

        self.assertEqual(
            frontend_fields,
            set(SearchInput.model_fields),
        )

    def test_search_radius_contract(self):
        """화면의 지름 1/2/3km를 서버 반경으로 변환할 수 있는지 검증."""
        for diameter in (1, 2, 3):
            request = SearchInput.model_validate({
                "center": {"lat": 37.498, "lng": 127.027},
                "radius_km": diameter / 2,
                "connector_types": ["FAST"],
                "region_filters": [],
            })

            self.assertEqual(request.radius_km, diameter / 2)

    def test_search_response_contract(self):
        """프론트가 사용하는 검색 응답 필드 확인."""
        required_fields = {
            "request_id",
            "status",
            "applied_request",
            "results",
            "critic_decision",
            "critic_findings",
        }

        self.assertTrue(
            required_fields.issubset(SearchResponse.model_fields)
        )


if __name__ == "__main__":
    unittest.main()
