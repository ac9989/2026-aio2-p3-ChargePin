"""In-memory Memory Keeper for the initial 1.0 preview."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class MemoryKeeper:
    handoffs: dict[str, dict[str, Any]] = field(default_factory=dict)
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    chat_contexts: dict[str, dict[str, Any]] = field(default_factory=dict)
    operation_events: list[dict[str, Any]] = field(default_factory=list)

    def start(self, request_id: str, handoff: dict[str, Any]) -> None:
        self.handoffs[request_id] = {**handoff, "retry_history": [], "audit_events": ["request_created"]}

    def update(self, request_id: str, **values: Any) -> None:
        self.handoffs.setdefault(request_id, {}).update(values)

    def record_audit(self, request_id: str, event: str) -> None:
        self.handoffs.setdefault(request_id, {}).setdefault("audit_events", []).append(event)

    def save_result(self, request_id: str, result: dict[str, Any]) -> None:
        self.results[request_id] = result
        self.handoffs.setdefault(request_id, {}).setdefault("audit_events", []).append("result_saved")

    def get_result(self, request_id: str) -> dict[str, Any] | None:
        return self.results.get(request_id)

    def set_chat_context(self, session_ref: str, context: dict[str, Any]) -> None:
        """Keep only the last confirmed search conditions for a logged-in chat session."""
        self.chat_contexts[session_ref] = context

    def get_chat_context(self, session_ref: str) -> dict[str, Any] | None:
        return self.chat_contexts.get(session_ref)

    def record_operation(self, event_type: str, status: str, *, request_id: str | None = None,
                         **details: Any) -> None:
        """Store safe operational facts only; never persist chat text or credentials."""
        event = {
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "status": status,
            **details,
        }
        if request_id:
            event["request_id"] = request_id
        self.operation_events.append(event)
        self.operation_events = self.operation_events[-200:]

    def add_retry(self, request_id: str, reason: str) -> int:
        history = self.handoffs.setdefault(request_id, {}).setdefault("retry_history", [])
        attempt = len(history) + 1
        history.append({
            "attempt": attempt,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
        })
        self.record_audit(request_id, "manual_retry_requested")
        return attempt
