"""Discovery findings store — historial de hallazgos (Fase D).

Persists discovery findings only (audit/historial). Never writes draws,
ranking, motor outputs, or historical lottery results.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class StoredFinding:
    id: str
    created_at: str
    investigation_id: str | None
    kind: str
    title: str
    level: str
    status: str  # published | discarded | draft
    tools: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DiscoveryFindingStore:
    """Process-local historial + optional DB audit hook."""

    def __init__(self, *, max_entries: int = 500):
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._items: list[StoredFinding] = []

    def save(self, finding: StoredFinding) -> StoredFinding:
        with self._lock:
            self._items.append(finding)
            if len(self._items) > self.max_entries:
                self._items = self._items[-self.max_entries :]
        return finding

    def list(
        self,
        *,
        status: str | None = None,
        limit: int = 50,
        investigation_id: str | None = None,
    ) -> list[StoredFinding]:
        with self._lock:
            items = list(self._items)
        if status:
            items = [x for x in items if x.status == status]
        if investigation_id:
            items = [x for x in items if x.investigation_id == investigation_id]
        return list(reversed(items))[: max(1, limit)]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


_STORE = DiscoveryFindingStore()


def get_discovery_store() -> DiscoveryFindingStore:
    return _STORE


def new_finding_id() -> str:
    return str(uuid.uuid4())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
