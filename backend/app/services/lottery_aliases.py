"""Resolución central de loterías (UUID, source_id, slug, nombre, alias)."""

from __future__ import annotations

import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lottery import LotteryAlias, LotteryLottery
from app.services.lottery_exceptions import LotteryQueryError
from app.services.lottery_permissions import (
    AMBIGUOUS_NACIONAL_DIA_CANDIDATES,
    CONFIRMED_PRIORITY_SOURCE_IDS,
    UNRESOLVED_AMBIGUOUS_ALIASES,
)


class ResolveStatus(str, Enum):
    RESOLVED = "resolved"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    PENDING_BUSINESS_MAPPING = "pending_business_mapping"
    INACTIVE = "inactive"


def normalize_lottery_alias(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = text.replace(".", " ").replace(":", " ").replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    # Equivalencias básicas
    text = text.replace("new york", "ny") if text.startswith("new york") or " new york " in f" {text} " else text
    # Re-normalize ny phrases kept as full phrases in map — apply after map keys also use normalize
    return text


def normalize_query(value: str) -> str:
    """Normalización con equivalencias ny/día usadas en resolución."""
    key = normalize_lottery_alias(value)
    # Map common variants onto confirmed keys
    replacements = {
        "new york dia": "ny dia",
        "new york día": "ny dia",
        "ny dia": "ny dia",
        "ny día": "ny dia",
        "new york noche": "ny noche",
        "ny noche": "ny noche",
        "new york 2 30": "new york 2:30",
        "new york 2.30": "new york 2:30",
        "new york 10 30": "new york 10:30",
        "new york 10.30": "new york 10:30",
    }
    # Recompute without collapsing new york→ny for colon times
    base = unicodedata.normalize("NFKD", value or "")
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    base = base.lower().strip()
    base = re.sub(r"\s+", " ", base)
    if base in replacements:
        return replacements[base]
    # Prefer confirmed map keys as stored
    key2 = unicodedata.normalize("NFKD", value or "")
    key2 = "".join(ch for ch in key2 if not unicodedata.combining(ch))
    key2 = key2.lower().strip()
    key2 = re.sub(r"\s+", " ", key2)
    return key2


@dataclass
class LotteryCandidate:
    source_id: int
    name: str
    confidence: str = "medium"
    id: uuid.UUID | None = None
    slug: str | None = None


@dataclass
class LotteryResolveResult:
    query: str
    status: ResolveStatus
    lottery: LotteryLottery | None = None
    candidates: list[LotteryCandidate] = field(default_factory=list)
    message: str | None = None

    @property
    def resolved(self) -> bool:
        return self.status == ResolveStatus.RESOLVED and self.lottery is not None


class LotteryResolver:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(self, lottery: str, *, allow_inactive: bool = False) -> LotteryResolveResult:
        raw = (lottery or "").strip()
        if not raw:
            raise LotteryQueryError("LOTTERY_NOT_FOUND", "Parámetro lottery vacío")

        # UUID
        try:
            lid = uuid.UUID(raw)
            row = await self.db.get(LotteryLottery, lid)
            if row:
                return self._from_row(raw, row, allow_inactive=allow_inactive)
        except ValueError:
            pass

        # source_id numérico
        if raw.isdigit():
            row = (
                await self.db.execute(
                    select(LotteryLottery).where(LotteryLottery.source_id == int(raw))
                )
            ).scalar_one_or_none()
            if row:
                return self._from_row(raw, row, allow_inactive=allow_inactive)

        key = normalize_query(raw)

        # Nacional Día / ambiguos pendientes
        if key in UNRESOLVED_AMBIGUOUS_ALIASES or key in {"nacional dia", "nacional día", "nacional"}:
            candidates = [
                LotteryCandidate(source_id=c["source_id"], name=c["name"], confidence=c["confidence"])
                for c in AMBIGUOUS_NACIONAL_DIA_CANDIDATES
            ]
            # Enrich with DB ids if present
            for cand in candidates:
                lot = (
                    await self.db.execute(
                        select(LotteryLottery).where(LotteryLottery.source_id == cand.source_id)
                    )
                ).scalar_one_or_none()
                if lot:
                    cand.id = lot.id
                    cand.slug = lot.slug
            return LotteryResolveResult(
                query=raw,
                status=ResolveStatus.PENDING_BUSINESS_MAPPING,
                candidates=candidates,
                message=(
                    "El alias «Nacional Día» no tiene mapping definitivo. "
                    "Candidatos: La Primera Tarde (20) y La Suerte MD (21)."
                ),
            )

        # Confirmed static aliases
        source_id = CONFIRMED_PRIORITY_SOURCE_IDS.get(key)
        # Also try ny variants stored in map
        if source_id is None:
            for alias, sid in CONFIRMED_PRIORITY_SOURCE_IDS.items():
                if normalize_query(alias) == key or alias == key:
                    source_id = sid
                    break

        if source_id is not None:
            # Guard against confusing Loto Real / Loto Leidsa with bare aliases
            row = (
                await self.db.execute(
                    select(LotteryLottery).where(LotteryLottery.source_id == source_id)
                )
            ).scalar_one_or_none()
            if row:
                return self._from_row(raw, row, allow_inactive=allow_inactive)

        # DB aliases table
        alias_row = (
            await self.db.execute(
                select(LotteryAlias).where(LotteryAlias.normalized_alias == key)
            )
        ).scalar_one_or_none()
        if alias_row:
            row = await self.db.get(LotteryLottery, alias_row.lottery_id)
            if row:
                return self._from_row(raw, row, allow_inactive=allow_inactive)

        # slug / normalized_name / name
        rows = (
            await self.db.execute(
                select(LotteryLottery).where(
                    or_(
                        LotteryLottery.slug == raw,
                        LotteryLottery.slug == key.replace(" ", "-"),
                        LotteryLottery.normalized_name == key,
                        LotteryLottery.name.ilike(raw),
                    )
                )
            )
        ).scalars().all()

        if len(rows) == 1:
            return self._from_row(raw, rows[0], allow_inactive=allow_inactive)
        if len(rows) > 1:
            return LotteryResolveResult(
                query=raw,
                status=ResolveStatus.AMBIGUOUS,
                candidates=[
                    LotteryCandidate(
                        source_id=r.source_id,
                        name=r.name,
                        confidence="medium",
                        id=r.id,
                        slug=r.slug,
                    )
                    for r in rows
                ],
                message="Múltiples loterías coinciden con la consulta.",
            )

        return LotteryResolveResult(
            query=raw,
            status=ResolveStatus.NOT_FOUND,
            message=f"Lotería no encontrada: {raw}",
        )

    async def resolve_or_raise(self, lottery: str) -> LotteryLottery:
        result = await self.resolve(lottery)
        if result.status == ResolveStatus.PENDING_BUSINESS_MAPPING:
            raise LotteryQueryError(
                "LOTTERY_PENDING_MAPPING",
                result.message or "Mapping pendiente",
                details={"candidates": [c.__dict__ for c in result.candidates]},
            )
        if result.status == ResolveStatus.AMBIGUOUS:
            raise LotteryQueryError(
                "LOTTERY_AMBIGUOUS",
                result.message or "Lotería ambigua",
                details={"candidates": [c.__dict__ for c in result.candidates]},
            )
        if result.status == ResolveStatus.NOT_FOUND or not result.lottery:
            raise LotteryQueryError("LOTTERY_NOT_FOUND", result.message or "No encontrada")
        if result.status == ResolveStatus.INACTIVE:
            raise LotteryQueryError("LOTTERY_NOT_FOUND", result.message or "Lotería inactiva")
        return result.lottery

    def _from_row(
        self, query: str, row: LotteryLottery, *, allow_inactive: bool
    ) -> LotteryResolveResult:
        if row.is_aggregate:
            return LotteryResolveResult(
                query=query,
                status=ResolveStatus.INACTIVE,
                lottery=row,
                message="Elemento agregado, no es una lotería individual.",
            )
        if not row.active and not allow_inactive:
            return LotteryResolveResult(
                query=query,
                status=ResolveStatus.INACTIVE,
                lottery=row,
                message="Lotería inactiva.",
            )
        # Lottery 2.0: searchable gate (admin can block queries without deactivating)
        if hasattr(row, "is_searchable") and not row.is_searchable and not allow_inactive:
            return LotteryResolveResult(
                query=query,
                status=ResolveStatus.INACTIVE,
                lottery=row,
                message="Lotería no disponible para consulta.",
            )
        return LotteryResolveResult(query=query, status=ResolveStatus.RESOLVED, lottery=row)


# Compat helpers used by Fase 1/2
def is_ambiguous_nacional_dia(alias: str) -> bool:
    return normalize_query(alias) in UNRESOLVED_AMBIGUOUS_ALIASES or normalize_query(alias) in {
        "nacional dia",
        "nacional día",
        "nacional",
    }


def resolve_confirmed_source_id(alias: str) -> int | None:
    if is_ambiguous_nacional_dia(alias):
        return None
    key = normalize_query(alias)
    if key in CONFIRMED_PRIORITY_SOURCE_IDS:
        return CONFIRMED_PRIORITY_SOURCE_IDS[key]
    for a, sid in CONFIRMED_PRIORITY_SOURCE_IDS.items():
        if normalize_query(a) == key:
            return sid
    return None


def nacional_dia_candidates() -> list[dict]:
    return [dict(c) for c in AMBIGUOUS_NACIONAL_DIA_CANDIDATES]


def describe_alias_resolution(alias: str) -> dict:
    if is_ambiguous_nacional_dia(alias):
        return {
            "query": alias,
            "resolved": False,
            "ambiguous": True,
            "status": ResolveStatus.PENDING_BUSINESS_MAPPING.value,
            "candidates": nacional_dia_candidates(),
            "message": (
                "El alias «Nacional Día» no tiene mapping definitivo. "
                "Candidatos: La Primera Tarde (20) y La Suerte MD (21)."
            ),
        }
    source_id = resolve_confirmed_source_id(alias)
    if source_id is None:
        return {
            "query": alias,
            "resolved": False,
            "ambiguous": False,
            "status": ResolveStatus.NOT_FOUND.value,
            "candidates": [],
            "message": "Alias no reconocido.",
        }
    return {
        "query": alias,
        "resolved": True,
        "ambiguous": False,
        "status": ResolveStatus.RESOLVED.value,
        "source_id": source_id,
        "candidates": [],
        "message": None,
    }
