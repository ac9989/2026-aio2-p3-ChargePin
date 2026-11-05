"""In-memory Memory Keeper for the initial 1.0 preview."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryKeeper:
    handoffs: dict[str, dict[str, Any]] = field(default_factory=dict)
    results: dict[str, dict[str, Any]] = field(default_factory=dict)

    def start(self, request_id: str, handoff: dict[str, Any]) -> None:
        self.handoffs[request_id] = {**handoff, "retry_history": [], "audit_events": ["request_created"]}

    def update(self, request_id: str, **values: Any) -> None:
        self.handoffs.setdefault(request_id, {}).update(values)

    def save_result(self, request_id: str, result: dict[str, Any]) -> None:
        self.results[request_id] = result
        self.handoffs.setdefault(request_id, {}).setdefault("audit_events", []).append("result_saved")

    def get_result(self, request_id: str) -> dict[str, Any] | None:
        return self.results.get(request_id)
