"""Schemas de entrada/salida del motor (sin FastAPI) — compartidos por API y tests."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.models import OccurrenceLimit


class AnalyzeBody(BaseModel):
    observed_number: int = Field(..., ge=1, le=100)
    lottery_ids: list[UUID] = Field(..., min_length=1)
    occurrence_mode: Literal["last_k", "all"] = "last_k"
    occurrence_k: int | None = Field(default=None, ge=1, le=500)


def limit_from_body(body: AnalyzeBody) -> OccurrenceLimit:
    if body.occurrence_mode == "all":
        return OccurrenceLimit.all()
    if body.occurrence_k is None:
        raise ValueError(
            "occurrence_k is required when occurrence_mode=last_k "
            "(valores UI: 5, 10, 20; no hay default oculto en el motor)"
        )
    return OccurrenceLimit.last_k(int(body.occurrence_k))


def enrich_table_rows(table: str) -> list[dict[str, Any]]:
    cat = build_catalog()
    rows = cat.table1_rows if table == "table1" else cat.table2_rows
    code_map = (
        cat.table1_code_to_numbers if table == "table1" else cat.table2_code_to_numbers
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        d = r.to_dict()
        group = list(code_map.get(r.code, []))
        d["group_numbers"] = group
        d["group_label"] = f"Código {r.code}"
        out.append(d)
    return out
