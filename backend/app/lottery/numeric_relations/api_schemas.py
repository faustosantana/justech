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
    """Proyecta filas de catálogo con metadatos de auditoría (solo lectura)."""
    from app.lottery.numeric_relations.decimal_math import sum_literal_digits

    if table not in ("table1", "table2"):
        raise ValueError("table must be 'table1' or 'table2'")
    cat = build_catalog()
    rows = cat.table1_rows if table == "table1" else cat.table2_rows
    code_map = (
        cat.table1_code_to_numbers if table == "table1" else cat.table2_code_to_numbers
    )
    engine_ref = (
        "app.lottery.numeric_relations.table1.format_table1_digits"
        if table == "table1"
        else "app.lottery.numeric_relations.table2.format_table2_digits"
    )
    out: list[dict[str, Any]] = []
    for r in rows:
        d = r.to_dict()
        group = list(code_map.get(r.code, []))
        d["group_numbers"] = group
        d["group_label"] = f"Código {r.code}"
        d["literal_digit_sum"] = sum_literal_digits(r.visible_value)
        d["read_only"] = True
        d["editable"] = False
        d["engine_ref"] = engine_ref
        out.append(d)
    return out


def number_detail(n: int, table: Literal["table1", "table2"]) -> dict[str, Any]:
    """Detalle completo de un número en una tabla (sin mezclar T1/T2)."""
    from app.lottery.numeric_relations.constants import N_MAX, N_MIN
    from app.lottery.numeric_relations.decimal_math import validate_n

    validate_n(n)
    rows = enrich_table_rows(table)
    row = next((r for r in rows if int(r["number"]) == int(n)), None)
    if row is None:
        raise ValueError(f"number {n} not found in {table} (universe {N_MIN}..{N_MAX})")
    return {
        **row,
        "detail": {
            "number": n,
            "table": table,
            "operation": row.get("formula"),
            "decimal_value": row.get("visible_value"),
            "exact_digit_chain": row.get("digits_without_point"),
            "literal_sum": row.get("literal_digit_sum"),
            "code": row.get("code"),
            "group_members": row.get("group_numbers"),
            "engine_ref": row.get("engine_ref"),
            "read_only": True,
        },
        "source": "NumericRelationsService/catalog",
        "tables_are_separate": True,
    }
