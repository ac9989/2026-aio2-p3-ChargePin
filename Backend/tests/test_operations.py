import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.operations import compose_platform_snapshot, healing_snapshot


class OperationsSnapshotTests(unittest.TestCase):
    def test_compose_snapshot_reports_service_health_without_runtime_values(self) -> None:
        with patch("app.operations._healthy", return_value=True), patch.dict(os.environ, {
            "OPENAI_PLANNER_MODEL": "gpt-4o-mini",
            "KECO_INFO_CACHE_TTL_SECONDS": "120",
            "CHARGEPIN_BACKEND_IMAGE": "ghcr.io/example/backend:abc",
            "CHARGEPIN_FRONTEND_IMAGE": "ghcr.io/example/frontend:abc",
        }, clear=False):
            snapshot = compose_platform_snapshot()

        self.assertEqual(snapshot["source"], "compose")
        self.assertEqual(
            [(item["name"], item["ready"]) for item in snapshot["workloads"]],
            [("backend", 1), ("frontend", 1)],
        )
        self.assertEqual(snapshot["config"][0]["keys"], 2)
        self.assertNotIn("gpt-4o-mini", str(snapshot))

    def test_healing_snapshot_keeps_only_safe_valid_jsonl_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "autoheal.jsonl"
            log_path.write_text(
                '{"timestamp_utc":"2026-11-08T00:00:00+00:00","event":"restart_attempt","container":"chargepin-frontend","token":"secret"}\n'
                'not-json\n'
                '{"timestamp_utc":"2026-11-08T00:00:09+00:00","event":"recovered","container":"chargepin-frontend","duration_seconds":8.489}\n'
                '{"timestamp_utc":"invalid","event":"recovered","container":"ignored"}\n',
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"AUTOHEAL_LOG_PATH": str(log_path)}, clear=False):
                snapshot = healing_snapshot()

        self.assertEqual([item["event"] for item in snapshot["events"]], ["restart_attempt", "recovered"])
        self.assertEqual(snapshot["events"][1]["duration_seconds"], 8.49)
        self.assertNotIn("secret", str(snapshot))

    def test_healing_snapshot_has_no_events_when_log_is_not_configured(self) -> None:
        with patch.dict(os.environ, {"AUTOHEAL_LOG_PATH": ""}, clear=False):
            self.assertEqual(healing_snapshot()["events"], [])


if __name__ == "__main__":
    unittest.main()
