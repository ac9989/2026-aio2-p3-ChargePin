import ast
import unittest
from pathlib import Path

from fastapi.routing import APIRoute

from app.main import app
from app.models import SearchInput, SearchResponse


ROOT = Path(__file__).resolve().parents[2]


class ApiContractTests(unittest.TestCase):

    @staticmethod
    def _path_text(node: ast.expr) -> str:
        """Preserve a route template when an API client path uses an f-string."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            parts: list[str] = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    parts.append(value.value)
                elif isinstance(value, ast.FormattedValue):
                    parts.append("{" + ast.unparse(value.value) + "}")
                else:
                    raise AssertionError("지원하지 않는 API 경로 형식")
            return "".join(parts)
        raise AssertionError("문자열 API 경로가 아닙니다.")

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

        expected_methods = {
            "health": ("GET", "/healthz", True),
            "login": ("POST", "/auth/login", False),
            "default_search": ("POST", "/search/default", False),
            "search": ("POST", "/search", False),
            "suggest_places": ("POST", "/places/suggest", False),
            "plan": ("POST", "/chat/plan", False),
            "confirm": ("POST", "/search/{request_id}/confirm", False),
            "boom": ("GET", "/boom/{scenario}", True),
            "ops_summary": ("GET", "/ops/summary", False),
            "ops_platform": ("GET", "/ops/platform", False),
            "ops_healing": ("GET", "/ops/healing", False),
            "retry_request": ("POST", "/ops/requests/{request_id}/retry", False),
            "refresh_cache": ("POST", "/ops/cache/refresh", False),
        }

        for name, (expected_method, expected_path, root_url) in expected_methods.items():
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
            path = self._path_text(calls[0].args[1])
            self.assertEqual(method, expected_method, name)
            self.assertEqual(path, expected_path, name)

            self.assertIn(
                (path if root_url else f"/api/v1{path}", method),
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
