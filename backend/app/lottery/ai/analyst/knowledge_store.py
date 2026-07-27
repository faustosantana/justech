"""Knowledge repository persistence (Fase E / v2.3.0).

Stores verified investigations with full evidence linkage.
Never writes lottery draws, ranking, or motor outputs.
"""

from __future__ import annotations

import json
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class KnowledgeRecord:
    id: str
    title: str
    created_at: str
    updated_at: str
    author: str = "Analista IA"
    original_question: str = ""
    executive_summary: str = ""
    full_investigation: str = ""
    evidences: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    evidence_level: str | None = None
    confidence: str | None = None
    # Versioning — never mix silently
    motor_version: str = "motor-v1.0"
    historical_version: str = "history-unknown"
    prompt_maestro_version: str = "v5"
    research_engine_version: str = "2.0"
    discovery_engine_version: str = "2.2.0"
    knowledge_engine_version: str = "2.3.0"
    # Taxonomy
    numbers: list[str] = field(default_factory=list)
    pairs: list[list[str]] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    table1_refs: list[str] = field(default_factory=list)
    table2_refs: list[str] = field(default_factory=list)
    lotteries: list[str] = field(default_factory=list)
    positions: list[str] = field(default_factory=list)
    years: list[int] = field(default_factory=list)
    period: str | None = None
    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    # Relations & citations
    related_ids: list[str] = field(default_factory=list)
    cited_ids: list[str] = field(default_factory=list)
    # Lifecycle
    favorite: bool = False
    pinned: bool = False
    archived: bool = False
    status: str = "verified"  # verified | draft | rejected | obsolete
    obsolete: bool = False
    obsolete_reason: str | None = None
    verification: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeRecord":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        payload = {k: v for k, v in (data or {}).items() if k in known}
        return cls(**payload)


DEFAULT_COLLECTIONS = (
    "Confirmaciones",
    "Tabla 1",
    "Tabla 2",
    "Casos históricos",
    "Comparaciones",
)


class KnowledgeStore:
    """File-backed + in-memory knowledge repository."""

    def __init__(self, path: Path | None = None):
        self.path = path or Path(
            os.environ.get("LOTTERY_KNOWLEDGE_PATH") or "/tmp/jaios_lottery_knowledge.json"
        )
        self._lock = threading.Lock()
        self._records: dict[str, KnowledgeRecord] = {}
        self._collections: dict[str, dict[str, Any]] = {
            name: {"name": name, "investigation_ids": [], "created_at": utc_now_iso()}
            for name in DEFAULT_COLLECTIONS
        }
        self._current_historical_version: str = "history-unknown"
        self._load()

    def set_current_historical_version(self, version: str) -> None:
        self._current_historical_version = version or "history-unknown"
        self._mark_obsolete_if_needed()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return
        for item in raw.get("records") or []:
            try:
                rec = KnowledgeRecord.from_dict(item)
                self._records[rec.id] = rec
            except Exception:  # noqa: BLE001
                continue
        for col in raw.get("collections") or []:
            if isinstance(col, dict) and col.get("name"):
                self._collections[str(col["name"])] = col
        if raw.get("current_historical_version"):
            self._current_historical_version = str(raw["current_historical_version"])

    def _flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": utc_now_iso(),
            "current_historical_version": self._current_historical_version,
            "records": [r.to_dict() for r in self._records.values()],
            "collections": list(self._collections.values()),
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def save(self, record: KnowledgeRecord) -> KnowledgeRecord:
        with self._lock:
            record.updated_at = utc_now_iso()
            if record.historical_version != self._current_historical_version and self._current_historical_version != "history-unknown":
                if record.historical_version and record.historical_version != "history-unknown":
                    record.obsolete = True
                    record.obsolete_reason = (
                        "Esta investigación fue realizada con una versión anterior del histórico."
                    )
                    record.status = "obsolete"
            self._records[record.id] = record
            self._flush()
        return record

    def get(self, record_id: str) -> KnowledgeRecord | None:
        return self._records.get(record_id)

    def list_all(self, *, include_archived: bool = False) -> list[KnowledgeRecord]:
        items = list(self._records.values())
        if not include_archived:
            items = [r for r in items if not r.archived]
        items.sort(key=lambda r: (not r.pinned, not r.favorite, r.created_at), reverse=True)
        # pinned/favorite first: sort trick — redo
        items.sort(key=lambda r: (r.pinned, r.favorite, r.created_at), reverse=True)
        return items

    def delete(self, record_id: str) -> bool:
        with self._lock:
            if record_id not in self._records:
                return False
            del self._records[record_id]
            for col in self._collections.values():
                ids = list(col.get("investigation_ids") or [])
                if record_id in ids:
                    col["investigation_ids"] = [x for x in ids if x != record_id]
            self._flush()
            return True

    def upsert_collection(self, name: str, investigation_ids: list[str] | None = None) -> dict[str, Any]:
        with self._lock:
            col = self._collections.get(name) or {
                "name": name,
                "investigation_ids": [],
                "created_at": utc_now_iso(),
            }
            if investigation_ids is not None:
                col["investigation_ids"] = list(dict.fromkeys(investigation_ids))
            col["updated_at"] = utc_now_iso()
            self._collections[name] = col
            self._flush()
            return dict(col)

    def list_collections(self) -> list[dict[str, Any]]:
        return list(self._collections.values())

    def _mark_obsolete_if_needed(self) -> None:
        changed = False
        with self._lock:
            for rec in self._records.values():
                if (
                    rec.historical_version
                    and rec.historical_version != "history-unknown"
                    and self._current_historical_version != "history-unknown"
                    and rec.historical_version != self._current_historical_version
                ):
                    if not rec.obsolete:
                        rec.obsolete = True
                        rec.obsolete_reason = (
                            "Esta investigación fue realizada con una versión anterior del histórico."
                        )
                        rec.status = "obsolete"
                        changed = True
            if changed:
                self._flush()


_STORE: KnowledgeStore | None = None


def get_knowledge_store() -> KnowledgeStore:
    global _STORE
    if _STORE is None:
        _STORE = KnowledgeStore()
    return _STORE
