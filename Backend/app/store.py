"""In-memory Memory Keeper for the initial 1.0 preview."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .logging_setup import append_operation_log
from .persistence import PostgresOperationStore


@dataclass
class MemoryKeeper:
    handoffs: dict[str, dict[str, Any]] = field(default_factory=dict)
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    chat_contexts: dict[str, dict[str, Any]] = field(default_factory=dict)
    operation_events: list[dict[str, Any]] = field(default_factory=list)
    event_store: PostgresOperationStore = field(default_factory=PostgresOperationStore)

    def _write(self, event_type: str, status: str, *, request_id: str | None = None,
               level: str = "INFO", **details: Any) -> None:
        """Persist safe operational facts without retaining chat text or secrets."""
        event: dict[str, Any] = {
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "status": status,
            **details,
        }
        if request_id:
            event["request_id"] = request_id
        safe_record = append_operation_log(event, level=level)
        if safe_record is not None:
            self.event_store.record(safe_record)

    def start(self, request_id: str, handoff: dict[str, Any]) -> None:
        self.handoffs[request_id] = {**handoff, "retry_history": [], "audit_events": ["request_created"]}
        # Store the handoff shape, not its values. ``raw_input`` is deliberately
        # excluded even as a field name so an audit log cannot imply retention.
        fields = sorted(key for key in handoff if key not in {"raw_input", "message", "content"})
        self._write("handoff", "created", request_id=request_id, handoff_fields=fields)

    def update(self, request_id: str, **values: Any) -> None:
        self.handoffs.setdefault(request_id, {}).update(values)
        fields = sorted(key for key in values if key not in {"raw_input", "message", "content"})
        self._write("handoff", "updated", request_id=request_id, handoff_fields=fields)

    def record_audit(self, request_id: str, event: str) -> None:
        self.handoffs.setdefault(request_id, {}).setdefault("audit_events", []).append(event)
        self._write("audit", "recorded", request_id=request_id, audit_event=event)

    def save_result(self, request_id: str, result: dict[str, Any]) -> None:
        self.results[request_id] = result
        self.handoffs.setdefault(request_id, {}).setdefault("audit_events", []).append("result_saved")
        self._write(
            "result",
            str(result.get("status", "unknown")),
            request_id=request_id,
            critic_decision=result.get("critic_decision"),
            result_count=len(result.get("results", [])) if isinstance(result.get("results"), list) else 0,
        )

    def get_result(self, request_id: str) -> dict[str, Any] | None:
        return self.results.get(request_id)

    def set_chat_context(self, session_ref: str, context: dict[str, Any]) -> None:
        """Keep only the last confirmed search conditions for a logged-in chat session."""
        self.chat_contexts[session_ref] = context
        self._write("chat_context", "updated", context_fields=sorted(context))

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
        level = "ERROR" if event_type == "agent_error" or status == "failed" else "INFO"
        self._write(event_type, status, request_id=request_id, level=level, **details)

    def add_retry(self, request_id: str, reason: str, *, kind: str = "manual") -> int:
        """Record a bounded retry without retaining provider payloads or user text."""
        history = self.handoffs.setdefault(request_id, {}).setdefault("retry_history", [])
        attempt = len(history) + 1
        history.append({
            "attempt": attempt,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "reason": reason,
        })
        self._write(
            "retry_history",
            "recorded",
            request_id=request_id,
            attempt=attempt,
            kind=kind,
            reason=reason,
        )
        self.record_audit(request_id, f"{kind}_retry_requested")
        return attempt

    def persisted_events(self, limit: int = 200, *, since: datetime | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Use durable events when available, otherwise keep the live-memory view."""
        stored = self.event_store.recent(limit, since=since)
        state = self.event_store.snapshot()
        if state["available"]:
            return stored, state
        fallback = self.operation_events[-limit:]
        if since is not None:
            fallback = [event for event in fallback if _event_time(event.get("occurred_at")) >= since]
        return list(reversed(fallback)), state


def _event_time(value: Any) -> datetime:
    """Best-effort timestamp parser for the in-memory fallback only."""
    if not isinstance(value, str):
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
