"""J-10L — Política pura del universo activo (sin SQLAlchemy)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Sequence
from uuid import UUID

EXPECTED_PRODUCT_SEVEN_NAMES = (
    "Lotería Nacional",
    "Quiniela Leidsa",
    "Quiniela Loteka",
    "Gana Más",
    "Quiniela Real",
    "New York 2:30",
    "New York 10:30",
)

SEED_FEATURED_SEVEN_NAMES = (
    "Quiniela Leidsa",
    "Quiniela Loteka",
    "Loteria Nacional",
    "Loto Leidsa",
    "Quiniela Real",
    "Loto Real",
    "Gana Mas",
)

ANALYSIS_SCOPE_LABEL = "FEATURED_SEVEN"

ACTIVE_ANALYSIS_USER_REPLY = (
    "El análisis utiliza las loterías activas configuradas en el sistema "
    "(únicamente las destacadas). Las fuentes archivadas no participan."
)


class AnalysisScope(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


@dataclass(frozen=True)
class ActiveLottery:
    id: str
    name: str
    slug: str | None = None

    @property
    def analysis_scope(self) -> AnalysisScope:
        return AnalysisScope.ACTIVE


def analysis_scope_for_featured(is_featured: bool) -> AnalysisScope:
    return AnalysisScope.ACTIVE if is_featured else AnalysisScope.ARCHIVED


def scope_set_hash(lottery_ids: Sequence[str]) -> str:
    norm = ",".join(sorted({str(x).lower() for x in lottery_ids}))
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def filter_to_active_ids(
    requested: Iterable[str | UUID],
    active_ids: set[str],
) -> tuple[list[str], list[str]]:
    accepted: list[str] = []
    rejected: list[str] = []
    seen: set[str] = set()
    for raw in requested:
        lid = str(raw)
        if lid in seen:
            continue
        seen.add(lid)
        if lid in active_ids:
            accepted.append(lid)
        else:
            rejected.append(lid)
    return accepted, rejected


def build_analysis_scope_metadata(
    active: Sequence[ActiveLottery],
    *,
    rejected_ids: Sequence[str] | None = None,
    methodology_version: str | None = None,
) -> dict[str, Any]:
    ids = [x.id for x in active]
    meta: dict[str, Any] = {
        "analysis_scope": ANALYSIS_SCOPE_LABEL,
        "analysis_scope_enum": AnalysisScope.ACTIVE.value,
        "active_lottery_count": len(active),
        "active_lottery_ids": ids,
        "active_lottery_names": [x.name for x in active],
        "scope_set_hash": scope_set_hash(ids),
        "user_note": "Análisis realizado con las loterías activas (destacadas) configuradas en el sistema.",
    }
    if methodology_version:
        meta["methodology_version"] = methodology_version
    if rejected_ids:
        meta["ignored_non_active_lottery_ids"] = list(rejected_ids)
        meta["ignored_non_active_count"] = len(rejected_ids)
    return meta


def name_set_discrepancy(active_names: Sequence[str]) -> dict[str, Any]:
    active_norm = {n.strip().casefold() for n in active_names}
    expected_norm = {n.strip().casefold() for n in EXPECTED_PRODUCT_SEVEN_NAMES}
    seed_norm = {n.strip().casefold() for n in SEED_FEATURED_SEVEN_NAMES}
    return {
        "expected_product_count": 7,
        "active_count": len(active_names),
        "matches_expected_product_names": active_norm == expected_norm,
        "matches_seed_featured_names": active_norm == seed_norm,
        "missing_vs_product": sorted(expected_norm - active_norm),
        "extra_vs_product": sorted(active_norm - expected_norm),
        "note": (
            "Si difiere, no alterar DB automáticamente. "
            "Ajustar is_featured solo con acción administrativa deliberada."
        ),
    }
