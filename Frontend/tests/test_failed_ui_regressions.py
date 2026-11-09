"""Structural regression checks for the historically failing Streamlit wiring.

These tests inspect the shipped UI functions without importing a Streamlit server.
A browser smoke test remains necessary before claiming end-to-end success.
"""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def definition(path: str, name: str) -> ast.FunctionDef:
    module = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    matches = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name]
    assert len(matches) == 1
    return matches[0]


def invoked(node: ast.AST, name: str) -> bool:
    return any(
        isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id == name
        for item in ast.walk(node)
    )


class FailedUiRegressionTests(unittest.TestCase):
    def test_dp02_default_search_is_wired_into_main(self):
        self.assertTrue(invoked(definition("app.py", "main"), "load_default_once"))

    def test_dp02_llm05_confirm_only_after_user_click(self):
        chat = definition("app.py", "render_chat")
        confirm_clicks = [
            node for node in ast.walk(chat) if isinstance(node, ast.If)
            and any(isinstance(item, ast.Constant) and item.value == "선택한 장소로 검색" for item in ast.walk(node.test))
        ]
        self.assertEqual(len(confirm_clicks), 1)
        self.assertTrue(invoked(confirm_clicks[0], "complete_chat_search"))
        calls = [item for item in ast.walk(chat)
                 if isinstance(item, ast.Call) and isinstance(item.func, ast.Name)
                 and item.func.id == "complete_chat_search"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0].args), 2)
        complete = definition("app.py", "complete_chat_search")
        self.assertEqual([arg.arg for arg in complete.args.args], ["plan", "candidate_id"])
        self.assertTrue(any(isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute)
                            and item.func.attr == "confirm" for item in ast.walk(complete)))

    def test_op02_dashboard_token_matches_login_session(self):
        source = (ROOT / "dashboard_view.py").read_text(encoding="utf-8")
        panel = definition("dashboard_view.py", "operations_action_panel")
        text = ast.get_source_segment(source, panel)
        self.assertIn('st.session_state.get("auth_token")', text)
        self.assertNotIn('st.session_state.get("access_token")', text)

    def test_op02_production_compose_enables_backend_operations_panel(self):
        compose = (ROOT.parent / "compose.prod.yml").read_text(encoding="utf-8")
        frontend = compose.split("\\n  frontend:\\n", 1)
        self.assertEqual(len(frontend), 2, "production frontend service missing")
        self.assertIn('CHARGEPIN_DASHBOARD_SERVER_OPS: "true"', frontend[1])


if __name__ == "__main__":
    unittest.main()
