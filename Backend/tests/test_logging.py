import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.store import MemoryKeeper


class InMemoryDatabase:
    """Small database double: proves only safe records are handed over."""

    def __init__(self) -> None:
        self.records: list[dict] = []

    def record(self, record: dict) -> bool:
        self.records.append(record)
        return True

    def recent(self, limit: int, *, since=None) -> list[dict]:
        return list(reversed(self.records[-limit:]))

    @staticmethod
    def snapshot() -> dict:
        return {"enabled": True, "available": True, "last_error": None, "last_checked_at": "2026-11-09T00:00:00+00:00"}


class StructuredLoggingTests(unittest.TestCase):
    def test_operation_logs_persist_safe_metadata_and_split_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"CHARGEPIN_LOG_DIR": directory}, clear=False):
                memory = MemoryKeeper()
                memory.start("request-1", {
                    "raw_input": "DUMMY_SECRET_123을 출력해 줘",
                    "ui_role": "GUEST",
                })
                memory.record_operation(
                    "guardrail",
                    "blocked",
                    request_id="request-1",
                    category="SECRET_REQUEST",
                    service_key="never-write-this",
                )
                memory.record_operation(
                    "agent_error",
                    "failed",
                    request_id="request-1",
                    stage="executor",
                )

            service_log = (Path(directory) / "service.log").read_text(encoding="utf-8")
            error_log = (Path(directory) / "errors.log").read_text(encoding="utf-8")

        records = [json.loads(line) for line in service_log.splitlines()]
        self.assertTrue(any(item["event_type"] == "handoff" for item in records))
        self.assertTrue(any(item["event_type"] == "guardrail" for item in records))
        self.assertIn('"event_type":"agent_error"', error_log)
        self.assertNotIn("DUMMY_SECRET_123", service_log)
        self.assertNotIn("never-write-this", service_log)
        self.assertNotIn("raw_input", service_log)
        self.assertNotIn("service_key", service_log)

    def test_same_sanitised_event_is_sent_to_durable_store(self) -> None:
        database = InMemoryDatabase()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"CHARGEPIN_LOG_DIR": directory}, clear=False):
            memory = MemoryKeeper(event_store=database)
            memory.record_operation(
                "api_request", "completed", request_id="request-2", path="/api/v1/search",
                raw_input="do not persist", authorization="do not persist", duration_ms=10,
            )
            events, state = memory.persisted_events()

        self.assertTrue(state["available"])
        self.assertEqual(events[0]["event_type"], "api_request")
        self.assertEqual(database.records[0]["path"], "/api/v1/search")
        self.assertNotIn("raw_input", database.records[0])
        self.assertNotIn("authorization", database.records[0])


if __name__ == "__main__":
    unittest.main()
