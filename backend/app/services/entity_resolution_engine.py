"""Entity Resolution Engine — Fase 4 Knowledge Engine."""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _normalize(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^\w\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


@dataclass
class ResolvedEntity:
    entity_id: str
    entity_type: str
    canonical_name: str
    matched_alias: str
    match_kind: str  # exact | alias | semantic | token
    confidence: float
    aliases: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# Seed corporativo — extensible vía DB en migración 023
SEED_ENTITIES: list[dict] = [
    {
        "id": "client-ademi",
        "type": "cliente",
        "canonical": "Banco Múltiple Ademi",
        "aliases": ["ademi", "banco ademi", "banco multiple ademi", "banco múltiple ademi", "bancomultiple ademi"],
    },
    {
        "id": "client-capital-dbg",
        "type": "cliente",
        "canonical": "Capital DBG",
        "aliases": ["capital dbg", "capital", "dbg", "capital bank dbg"],
    },
    {
        "id": "client-la-sociedad",
        "type": "cliente",
        "canonical": "Grupo La Sociedad",
        "aliases": ["la sociedad", "grupo la sociedad", "sociedad"],
    },
    {
        "id": "client-farmatrix",
        "type": "cliente",
        "canonical": "Farma Trix",
        "aliases": ["farmatrix", "farma trix", "farma-trix", "farm trix"],
    },
    {
        "id": "product-dell-latitude",
        "type": "producto",
        "canonical": "Dell Latitude",
        "aliases": ["laptop dell", "dell latitude", "latitude 5450", "dell 5450", "dell laptops"],
    },
    {
        "id": "product-papel-350",
        "type": "producto",
        "canonical": "Papel térmico 350",
        "aliases": ["papel 350", "rollo 350", "papel térmico 350", "papel termico 350", "rollo térmico 350"],
    },
    {
        "id": "doc-rpe",
        "type": "documento",
        "canonical": "Registro de Proveedores del Estado (RPE)",
        "aliases": ["rpe", "registro proveedor estado", "registro de proveedores", "registro proveedores estado"],
    },
    {
        "id": "doc-dgii",
        "type": "documento",
        "canonical": "Certificación DGII",
        "aliases": ["dgii", "certificación dgii", "certificacion dgii", "impuestos internos", "certificado dgii"],
    },
    {
        "id": "doc-tss",
        "type": "documento",
        "canonical": "Certificación TSS",
        "aliases": ["tss", "certificación tss", "seguridad social"],
    },
    {
        "id": "concept-computadoras",
        "type": "concepto",
        "canonical": "Equipos de cómputo",
        "aliases": ["computadoras", "computadores", "laptops", "equipos informáticos", "pc"],
    },
]


class EntityResolutionEngine:
    """Resuelve consultas a entidades canónicas con alias y sinónimos."""

    def __init__(self, db: AsyncSession | None = None, tenant_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self._entities = list(SEED_ENTITIES)

    async def load(self) -> None:
        if not self.db or not self.tenant_id:
            return
        try:
            from app.models.knowledge_entity import KnowledgeEntity

            result = await self.db.execute(
                select(KnowledgeEntity).where(KnowledgeEntity.tenant_id == self.tenant_id)
            )
            for row in result.scalars().all():
                self._entities.append({
                    "id": str(row.id),
                    "type": row.entity_type,
                    "canonical": row.canonical_name,
                    "aliases": list(row.aliases or []),
                })
        except Exception:
            pass

    def resolve(self, query: str, *, limit: int = 5) -> list[ResolvedEntity]:
        q_norm = _normalize(query)
        if not q_norm:
            return []

        tokens = q_norm.split()
        found: list[ResolvedEntity] = []

        for ent in self._entities:
            canonical = ent["canonical"]
            aliases = [canonical] + list(ent.get("aliases") or [])
            best: ResolvedEntity | None = None

            for alias in aliases:
                a_norm = _normalize(alias)
                if not a_norm:
                    continue
                kind = "token"
                conf = 0.5

                if q_norm == a_norm:
                    kind, conf = "exact", 1.0
                elif a_norm == q_norm or canonical.lower() == query.strip().lower():
                    kind, conf = "exact", 0.98
                elif q_norm in a_norm or a_norm in q_norm:
                    kind, conf = "alias", 0.92
                elif tokens and all(tok in a_norm for tok in tokens if len(tok) >= 2):
                    kind, conf = "semantic", 0.78
                elif tokens and any(tok in a_norm for tok in tokens if len(tok) >= 3):
                    kind, conf = "token", 0.65
                else:
                    continue

                candidate = ResolvedEntity(
                    entity_id=ent["id"],
                    entity_type=ent["type"],
                    canonical_name=canonical,
                    matched_alias=alias,
                    match_kind=kind,
                    confidence=conf,
                    aliases=[_normalize(a) for a in aliases[:12]],
                )
                if best is None or candidate.confidence > best.confidence:
                    best = candidate

            if best and best.confidence >= 0.65:
                found.append(best)

        found.sort(key=lambda e: e.confidence, reverse=True)
        return found[:limit]

    def expand_search_terms(self, query: str, entities: list[ResolvedEntity] | None = None) -> list[str]:
        terms = {_normalize(query)}
        for ent in entities or self.resolve(query):
            terms.add(_normalize(ent.canonical_name))
            for alias in ent.aliases:
                if alias:
                    terms.add(alias)
        return [t for t in terms if len(t) >= 2]

    @staticmethod
    def primary_entity(entities: list[ResolvedEntity]) -> ResolvedEntity | None:
        return entities[0] if entities else None
