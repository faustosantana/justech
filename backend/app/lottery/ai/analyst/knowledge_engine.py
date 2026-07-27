"""Knowledge Engine — Fase E / v2.3.0.

Repositorio de investigaciones verificadas (no aprendizaje automático).
No modifica Motor, Tabla 1/2, Ranking, Histórico, Prompt Maestro,
Research Engine, Discovery Engine, Conversation Brain ni Planner.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.lottery.ai.analyst.knowledge_store import (
    DEFAULT_COLLECTIONS,
    KnowledgeRecord,
    KnowledgeStore,
    get_knowledge_store,
    utc_now_iso,
)
from app.lottery.numeric_relations.analysis_engine.motor_v1_freeze import MOTOR_PRODUCT_VERSION

KNOWLEDGE_ENGINE_VERSION = "2.3.0"
KNOWLEDGE_ENGINE_ENABLED = True
AUTHOR_DEFAULT = "Analista IA"
PROMPT_MAESTRO_VERSION = "v5"
RESEARCH_ENGINE_VERSION = "2.0"
DISCOVERY_ENGINE_VERSION = "2.2.0"

EXPORT_FORMATS = ("pdf", "markdown", "word", "excel", "json")

_NUM_RE = re.compile(r"\b(\d{1,2})\b")
_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_PAIR_RE = re.compile(r"\b(\d{1,2})\s*(?:vs|y|/|\+|contra)\s*(\d{1,2})\b", re.I)


@dataclass
class KnowledgeSaveRequest:
    title: str | None = None
    original_question: str = ""
    executive_summary: str = ""
    full_investigation: str = ""
    evidences: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    evidence_level: str | None = None
    confidence: str | None = None
    tags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    collections: list[str] = field(default_factory=list)
    cited_ids: list[str] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)
    pairs: list[list[str]] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    table1_refs: list[str] = field(default_factory=list)
    table2_refs: list[str] = field(default_factory=list)
    lotteries: list[str] = field(default_factory=list)
    positions: list[str] = field(default_factory=list)
    years: list[int] = field(default_factory=list)
    period: str | None = None
    motor_version: str | None = None
    historical_version: str | None = None
    prompt_maestro_version: str | None = None
    research_engine_version: str | None = None
    discovery_engine_version: str | None = None
    finished_ok: bool = True
    discarded: bool = False
    has_errors: bool = False
    author: str = AUTHOR_DEFAULT


@dataclass
class KnowledgeSearchQuery:
    number: str | None = None
    pair: list[str] | None = None
    group: str | None = None
    table1: str | None = None
    table2: str | None = None
    lottery: str | None = None
    position: str | None = None
    year: int | None = None
    period: str | None = None
    keyword: str | None = None
    tags: list[str] | None = None
    collection: str | None = None
    favorite_only: bool = False
    pinned_only: bool = False
    include_archived: bool = False
    include_obsolete: bool = True
    motor_version: str | None = None
    historical_version: str | None = None
    limit: int = 50


class KnowledgeEngine:
    """Verified investigation repository."""

    def __init__(self, store: KnowledgeStore | None = None):
        self.store = store or get_knowledge_store()
        self.enabled = KNOWLEDGE_ENGINE_ENABLED
        self.version = KNOWLEDGE_ENGINE_VERSION

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "version": self.version,
            "kind": "verified_investigation_repository",
            "not_ml": True,
            "export_formats_planned": list(EXPORT_FORMATS),
            "export_generation_implemented": False,
            "default_collections": list(DEFAULT_COLLECTIONS),
            "current_historical_version": self.store._current_historical_version,
            "count": len(self.store.list_all(include_archived=True)),
        }

    def set_historical_version(self, version: str) -> None:
        self.store.set_current_historical_version(version)

    def can_save(self, req: KnowledgeSaveRequest) -> tuple[bool, list[str]]:
        reasons: list[str] = []
        if not req.finished_ok:
            reasons.append("investigación no terminó correctamente")
        if req.discarded:
            reasons.append("investigación descartada")
        if req.has_errors:
            reasons.append("investigación contiene errores")
        if not (req.evidences or []):
            reasons.append("evidencia insuficiente (sin evidencias)")
        if not (req.full_investigation or "").strip() and not (req.executive_summary or "").strip():
            reasons.append("falta investigación completa o resumen ejecutivo")
        # Never conclusions-only: require evidence OR full text with evidence
        if (req.executive_summary or "").strip() and not (req.evidences or []) and not (req.full_investigation or "").strip():
            reasons.append("nunca almacenar únicamente conclusiones")
        return (len(reasons) == 0, reasons)

    def save(self, req: KnowledgeSaveRequest) -> dict[str, Any]:
        ok, reasons = self.can_save(req)
        if not ok:
            return {
                "saved": False,
                "reasons": reasons,
                "knowledge_engine_version": self.version,
            }

        extracted = self._extract_taxonomy(req)
        now = utc_now_iso()
        rid = f"kn-{uuid.uuid4().hex[:12]}"
        motor_v = req.motor_version or f"motor-v{MOTOR_PRODUCT_VERSION}"
        hist_v = req.historical_version or self.store._current_historical_version

        record = KnowledgeRecord(
            id=rid,
            title=(req.title or self._default_title(req)).strip()[:240],
            created_at=now,
            updated_at=now,
            author=req.author or AUTHOR_DEFAULT,
            original_question=req.original_question or "",
            executive_summary=req.executive_summary or "",
            full_investigation=req.full_investigation or "",
            evidences=list(req.evidences or []),
            tools_used=list(req.tools_used or []),
            evidence_level=req.evidence_level,
            confidence=req.confidence,
            motor_version=motor_v,
            historical_version=hist_v,
            prompt_maestro_version=req.prompt_maestro_version or PROMPT_MAESTRO_VERSION,
            research_engine_version=req.research_engine_version or RESEARCH_ENGINE_VERSION,
            discovery_engine_version=req.discovery_engine_version or DISCOVERY_ENGINE_VERSION,
            knowledge_engine_version=self.version,
            numbers=extracted["numbers"],
            pairs=extracted["pairs"],
            groups=extracted["groups"],
            table1_refs=extracted["table1_refs"],
            table2_refs=extracted["table2_refs"],
            lotteries=extracted["lotteries"],
            positions=extracted["positions"],
            years=extracted["years"],
            period=req.period or extracted.get("period"),
            keywords=extracted["keywords"],
            tags=list(dict.fromkeys([*(req.tags or []), *extracted["tags"]])),
            collections=list(req.collections or []),
            cited_ids=list(req.cited_ids or []),
            verification={
                "finished_ok": True,
                "sufficient_evidence": True,
                "discarded": False,
                "has_errors": False,
                "saved_at": now,
            },
        )

        # Citations integrity
        for cid in list(record.cited_ids):
            cited = self.store.get(cid)
            if cited is None:
                record.cited_ids = [x for x in record.cited_ids if x != cid]
            else:
                # Never mix versions silently — flag if cited from other versions
                if cited.motor_version != record.motor_version or cited.historical_version != record.historical_version:
                    record.tags = list(dict.fromkeys([*record.tags, "cita-version-distinta"]))
                    note = (
                        f"Cita {cid} usa motor={cited.motor_version}/histórico={cited.historical_version}; "
                        f"actual motor={record.motor_version}/histórico={record.historical_version}."
                    )
                    record.full_investigation = (record.full_investigation or "") + f"\n\n[AVISO CITAS] {note}"

        record.related_ids = self._compute_related(record)
        saved = self.store.save(record)

        # Auto-add to collections
        for cname in saved.collections:
            col = self.store.upsert_collection(cname)
            ids = list(col.get("investigation_ids") or [])
            if saved.id not in ids:
                ids.append(saved.id)
                self.store.upsert_collection(cname, ids)
        self._auto_assign_collections(saved)

        # Refresh related bidirectionally (light)
        self._link_bidirectional(saved)

        return {
            "saved": True,
            "investigation": saved.to_dict(),
            "knowledge_engine_version": self.version,
            "obsolescence_notice": saved.obsolete_reason if saved.obsolete else None,
        }

    def get(self, investigation_id: str) -> dict[str, Any] | None:
        rec = self.store.get(investigation_id)
        if not rec:
            return None
        payload = rec.to_dict()
        payload["related"] = [self.store.get(i).to_dict() for i in rec.related_ids if self.store.get(i)]
        payload["citations"] = [self.store.get(i).to_dict() for i in rec.cited_ids if self.store.get(i)]
        if rec.obsolete:
            payload["obsolescence_banner"] = (
                rec.obsolete_reason
                or "Esta investigación fue realizada con una versión anterior del histórico."
            )
        return payload

    def search(self, q: KnowledgeSearchQuery) -> dict[str, Any]:
        items = self.store.list_all(include_archived=q.include_archived)
        out: list[KnowledgeRecord] = []
        for rec in items:
            if not q.include_obsolete and rec.obsolete:
                continue
            if q.favorite_only and not rec.favorite:
                continue
            if q.pinned_only and not rec.pinned:
                continue
            # Version isolation: if filter set, exact match
            if q.motor_version and rec.motor_version != q.motor_version:
                continue
            if q.historical_version and rec.historical_version != q.historical_version:
                continue
            if q.number and str(q.number).zfill(2) not in [n.zfill(2) for n in rec.numbers]:
                # also check text
                if str(q.number) not in (rec.title + rec.original_question + rec.full_investigation):
                    continue
            if q.pair:
                want = sorted([str(x).zfill(2) for x in q.pair[:2]])
                pairs = [sorted([a.zfill(2), b.zfill(2)]) for a, b in rec.pairs if len(a) and len(b)]
                if want not in pairs and not any(
                    want[0] in (rec.title + " " + rec.original_question)
                    and want[1] in (rec.title + " " + rec.original_question)
                    for _ in [0]
                ):
                    continue
            if q.group and q.group.lower() not in [g.lower() for g in rec.groups]:
                continue
            if q.table1 and q.table1 not in rec.table1_refs and "tabla 1" not in " ".join(rec.tags).lower():
                if "tabla 1" not in (rec.title + rec.full_investigation).lower():
                    continue
            if q.table2 and q.table2 not in rec.table2_refs and "tabla 2" not in " ".join(rec.tags).lower():
                if "tabla 2" not in (rec.title + rec.full_investigation).lower():
                    continue
            if q.lottery and q.lottery.lower() not in [x.lower() for x in rec.lotteries]:
                if q.lottery.lower() not in (rec.title + rec.full_investigation).lower():
                    continue
            if q.position and q.position.lower() not in [x.lower() for x in rec.positions]:
                continue
            if q.year is not None and int(q.year) not in rec.years:
                if str(q.year) not in (rec.title + rec.original_question + (rec.period or "")):
                    continue
            if q.period and (rec.period or "").lower() != q.period.lower():
                if q.period.lower() not in (rec.title + rec.full_investigation).lower():
                    continue
            if q.keyword:
                blob = " ".join(
                    [
                        rec.title,
                        rec.original_question,
                        rec.executive_summary,
                        rec.full_investigation,
                        " ".join(rec.keywords),
                        " ".join(rec.tags),
                    ]
                ).lower()
                if q.keyword.lower() not in blob:
                    continue
            if q.tags:
                tags_l = {t.lower() for t in rec.tags}
                if not all(t.lower() in tags_l for t in q.tags):
                    continue
            if q.collection and q.collection not in rec.collections:
                continue
            out.append(rec)
            if len(out) >= max(1, min(q.limit, 200)):
                break
        return {
            "count": len(out),
            "items": [r.to_dict() for r in out],
            "knowledge_engine_version": self.version,
            "query": {
                "number": q.number,
                "pair": q.pair,
                "group": q.group,
                "table1": q.table1,
                "table2": q.table2,
                "lottery": q.lottery,
                "position": q.position,
                "year": q.year,
                "period": q.period,
                "keyword": q.keyword,
                "tags": q.tags,
                "collection": q.collection,
            },
        }

    def set_favorite(self, investigation_id: str, favorite: bool = True) -> dict[str, Any] | None:
        rec = self.store.get(investigation_id)
        if not rec:
            return None
        rec.favorite = bool(favorite)
        return self.store.save(rec).to_dict()

    def set_pinned(self, investigation_id: str, pinned: bool = True) -> dict[str, Any] | None:
        rec = self.store.get(investigation_id)
        if not rec:
            return None
        rec.pinned = bool(pinned)
        return self.store.save(rec).to_dict()

    def set_archived(self, investigation_id: str, archived: bool = True) -> dict[str, Any] | None:
        rec = self.store.get(investigation_id)
        if not rec:
            return None
        rec.archived = bool(archived)
        return self.store.save(rec).to_dict()

    def create_collection(self, name: str, investigation_ids: list[str] | None = None) -> dict[str, Any]:
        return self.store.upsert_collection(name, investigation_ids)

    def list_collections(self) -> list[dict[str, Any]]:
        return self.store.list_collections()

    def cite(self, investigation_id: str, cited_id: str) -> dict[str, Any] | None:
        """Attach a citation — never copy results without reference."""
        rec = self.store.get(investigation_id)
        cited = self.store.get(cited_id)
        if not rec or not cited:
            return None
        if cited_id not in rec.cited_ids:
            rec.cited_ids.append(cited_id)
        cite_line = f"\n\n[CITA] {cited.id} — {cited.title} ({cited.created_at})"
        if cite_line.strip() not in (rec.full_investigation or ""):
            rec.full_investigation = (rec.full_investigation or "") + cite_line
        if cited.motor_version != rec.motor_version or cited.historical_version != rec.historical_version:
            rec.tags = list(dict.fromkeys([*rec.tags, "cita-version-distinta"]))
        return self.store.save(rec).to_dict()

    def related_chain(self, investigation_id: str) -> dict[str, Any]:
        """Auto-related investigations (similarity graph)."""
        root = self.store.get(investigation_id)
        if not root:
            return {"found": False}
        related = []
        for rid in root.related_ids:
            r = self.store.get(rid)
            if r:
                related.append(
                    {
                        "id": r.id,
                        "title": r.title,
                        "relation_hint": self._relation_hint(root, r),
                        "obsolete": r.obsolete,
                    }
                )
        return {
            "found": True,
            "root": {"id": root.id, "title": root.title, "numbers": root.numbers},
            "related": related,
            "chain_example_style": True,
        }

    def export_plan(self, investigation_id: str, fmt: str) -> dict[str, Any]:
        """Architecture stub — generation not implemented yet."""
        fmt_n = (fmt or "").lower().strip()
        rec = self.store.get(investigation_id)
        return {
            "implemented": False,
            "format": fmt_n,
            "supported_planned": list(EXPORT_FORMATS),
            "accepted": fmt_n in EXPORT_FORMATS,
            "investigation_id": investigation_id,
            "available": rec is not None,
            "message": "Exportación preparada arquitectónicamente; generación aún no implementada.",
            "payload_preview_keys": list((rec.to_dict() if rec else {}).keys()),
        }

    def save_from_research_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Helper for chat/API — maps research output without mutating RE."""
        evidence = payload.get("evidences") or payload.get("evidence") or []
        if isinstance(evidence, dict):
            evidence = [evidence]
        req = KnowledgeSaveRequest(
            title=payload.get("title"),
            original_question=str(payload.get("original_question") or payload.get("question") or ""),
            executive_summary=str(payload.get("executive_summary") or payload.get("summary") or ""),
            full_investigation=str(payload.get("full_investigation") or payload.get("investigation") or payload.get("answer") or ""),
            evidences=list(evidence),
            tools_used=list(payload.get("tools_used") or payload.get("tools") or []),
            evidence_level=payload.get("evidence_level"),
            confidence=payload.get("confidence"),
            tags=list(payload.get("tags") or []),
            keywords=list(payload.get("keywords") or []),
            collections=list(payload.get("collections") or []),
            cited_ids=list(payload.get("cited_ids") or []),
            numbers=[str(x) for x in (payload.get("numbers") or [])],
            finished_ok=bool(payload.get("finished_ok", True)),
            discarded=bool(payload.get("discarded", False)),
            has_errors=bool(payload.get("has_errors", False)),
            historical_version=payload.get("historical_version"),
            motor_version=payload.get("motor_version"),
            period=payload.get("period"),
        )
        return self.save(req)

    # --- internals ---

    def _default_title(self, req: KnowledgeSaveRequest) -> str:
        q = (req.original_question or req.executive_summary or "Investigación").strip()
        return q[:120] if q else "Investigación verificada"

    def _extract_taxonomy(self, req: KnowledgeSaveRequest) -> dict[str, Any]:
        blob = " ".join(
            [
                req.title or "",
                req.original_question or "",
                req.executive_summary or "",
                req.full_investigation or "",
                " ".join(req.keywords or []),
                " ".join(req.tags or []),
            ]
        )
        numbers = list(dict.fromkeys([*(req.numbers or []), *[m.zfill(2) for m in _NUM_RE.findall(blob)]]))
        pairs = list(req.pairs or [])
        for a, b in _PAIR_RE.findall(blob):
            pairs.append([a.zfill(2), b.zfill(2)])
        years = list(dict.fromkeys([*(req.years or []), *[int(y) for y in _YEAR_RE.findall(blob)]]))
        tags = list(req.tags or [])
        keywords = list(req.keywords or [])
        low = blob.lower()
        if "tabla 1" in low or "t1" in low:
            tags.append("Tabla 1")
        if "tabla 2" in low or "t2" in low:
            tags.append("Tabla 2")
        if "confirm" in low:
            tags.append("Confirmaciones")
        if "compar" in low or " vs " in low:
            tags.append("Comparaciones")
        if "históric" in low or "historico" in low or "histórico" in low:
            tags.append("Casos históricos")
        lotteries = list(req.lotteries or [])
        for name in ("nacional", "loteka", "leidsa", "anguila", "cash4life", "mega", "florida"):
            if name in low and name.title() not in lotteries:
                lotteries.append(name.title() if name != "cash4life" else "Cash4Life")
        positions = list(req.positions or [])
        for pos in ("primera", "segunda", "tercera", "posición", "posicion"):
            if pos in low:
                positions.append(pos)
        groups = list(req.groups or [])
        table1 = list(req.table1_refs or [])
        table2 = list(req.table2_refs or [])
        if "Tabla 1" in tags and not table1:
            table1 = numbers[:3]
        if "Tabla 2" in tags and not table2:
            table2 = numbers[:3]
        return {
            "numbers": numbers[:20],
            "pairs": pairs[:20],
            "groups": groups,
            "table1_refs": table1,
            "table2_refs": table2,
            "lotteries": lotteries,
            "positions": list(dict.fromkeys(positions)),
            "years": years,
            "keywords": keywords,
            "tags": list(dict.fromkeys(tags)),
            "period": req.period,
        }

    def _compute_related(self, record: KnowledgeRecord) -> list[str]:
        scores: list[tuple[float, str]] = []
        for other in self.store.list_all(include_archived=True):
            if other.id == record.id:
                continue
            # Never mix versions in "same family" ranking — still show but lower score
            score = 0.0
            shared_nums = set(record.numbers) & set(other.numbers)
            score += 3.0 * len(shared_nums)
            if set(map(tuple, record.pairs)) & set(map(tuple, other.pairs)):
                score += 4.0
            shared_tags = set(t.lower() for t in record.tags) & set(t.lower() for t in other.tags)
            score += 1.5 * len(shared_tags)
            if record.years and other.years and set(record.years) & set(other.years):
                score += 2.0
            if record.motor_version == other.motor_version and record.historical_version == other.historical_version:
                score += 1.0
            else:
                score *= 0.5
            if score >= 3.0:
                scores.append((score, other.id))
        scores.sort(reverse=True)
        return [i for _, i in scores[:12]]

    def _link_bidirectional(self, record: KnowledgeRecord) -> None:
        for rid in record.related_ids:
            other = self.store.get(rid)
            if not other:
                continue
            if record.id not in other.related_ids:
                other.related_ids = list(dict.fromkeys([*other.related_ids, record.id]))[:12]
                self.store.save(other)

    def _relation_hint(self, a: KnowledgeRecord, b: KnowledgeRecord) -> str:
        shared = sorted(set(a.numbers) & set(b.numbers))
        if shared and ("vs" in b.title.lower() or "compar" in " ".join(b.tags).lower()):
            return f"Comparación {'/'.join(shared)}"
        if shared and b.years:
            return f"{shared[0]} durante {b.years[0]}"
        if "confirm" in " ".join(b.tags).lower():
            return f"Confirmaciones del {shared[0] if shared else 'caso'}"
        if shared:
            return f"Casos equivalentes del {shared[0]}"
        return "Investigación relacionada"

    def _auto_assign_collections(self, record: KnowledgeRecord) -> None:
        mapping = {
            "Confirmaciones": "Confirmaciones",
            "Tabla 1": "Tabla 1",
            "Tabla 2": "Tabla 2",
            "Casos históricos": "Casos históricos",
            "Comparaciones": "Comparaciones",
        }
        for tag, cname in mapping.items():
            if any(t.lower() == tag.lower() for t in record.tags) or cname in record.collections:
                col = self.store.upsert_collection(cname)
                ids = list(col.get("investigation_ids") or [])
                if record.id not in ids:
                    ids.append(record.id)
                    self.store.upsert_collection(cname, ids)
                if cname not in record.collections:
                    record.collections = list(dict.fromkeys([*record.collections, cname]))
                    self.store.save(record)


_ENGINE: KnowledgeEngine | None = None


def get_knowledge_engine() -> KnowledgeEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = KnowledgeEngine()
    return _ENGINE


def content_fingerprint(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]
