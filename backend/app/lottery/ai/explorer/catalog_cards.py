"""Read-only catalog cards for Lottery IA Explorer (in-memory cache; no DB/Motor)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Literal


def _parse_n(raw: Any) -> int | None:
    try:
        n = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if 1 <= n <= 100:
        return n
    return None


@lru_cache(maxsize=1)
def _catalog():
    from app.lottery.numeric_relations.catalog import build_catalog

    return build_catalog()


def clear_card_cache() -> None:
    _catalog.cache_clear()
    build_number_card.cache_clear()  # type: ignore[attr-defined]


@lru_cache(maxsize=128)
def build_number_card(n: int) -> dict[str, Any]:
    """Smart card for a single number (Tabla 1 + Tabla 2)."""
    cat = _catalog()
    t1_code = cat.table1_number_to_code.get(n)
    t1_companions: list[int] = []
    if t1_code is not None:
        t1_companions = [x for x in cat.get_table1_companions(t1_code) if x != n]

    try:
        t2_code = cat.get_table2_code_for_number(n)
    except KeyError:
        t2_code = None
    t2_neighbors = cat.get_table2_neighbors(n, exclude_self=True) if t2_code is not None else []

    return {
        "number": n,
        "label": f"{n:02d}",
        "table1": {
            "code": t1_code,
            "companions": t1_companions,
            "companions_count": len(t1_companions),
        },
        "table2": {
            "code": t2_code,
            "neighbors": t2_neighbors,
            "neighbors_count": len(t2_neighbors),
        },
        "actions": [
            "analizar",
            "comparar",
            "tabla1",
            "tabla2",
            "companeros",
            "vecinos",
            "historico",
            "coincidencias",
            "estadisticas",
            "abrir_investigacion",
        ],
        "source": "catalog_cache",
        "cached": True,
    }


def build_table_explorer(table: Literal["1", "2", "table1", "table2"]) -> dict[str, Any]:
    """Interactive table rows (catalog only)."""
    from app.lottery.numeric_relations.api_schemas import enrich_table_rows

    key = "table1" if table in {"1", "table1", "t1"} else "table2"
    rows = enrich_table_rows(key)
    interactive = []
    for r in rows:
        interactive.append(
            {
                "number": r.get("number"),
                "code": r.get("code"),
                "group_numbers": r.get("group_numbers") or [],
                "formula": r.get("formula"),
                "interactive": True,
            }
        )
    return {
        "table": "1" if key == "table1" else "2",
        "table_key": key,
        "rows": interactive,
        "row_count": len(interactive),
        "source": "catalog_cache",
        "cached": True,
    }


def build_compare_board(numbers: list[Any]) -> dict[str, Any]:
    """Multi-number comparison board from catalog cards."""
    nums: list[int] = []
    for raw in numbers:
        n = _parse_n(raw)
        if n is not None and n not in nums:
            nums.append(n)
    cards = [build_number_card(n) for n in nums[:6]]
    return {
        "numbers": nums[:6],
        "cards": cards,
        "dimensions": [
            "tabla1",
            "tabla2",
            "companeros",
            "vecinos",
            "coincidencias",
            "historico",
            "estadisticas",
        ],
        "source": "catalog_cache",
        "cached": True,
    }


def parse_numbers(raw: list[Any] | None) -> list[str]:
    out: list[str] = []
    for item in raw or []:
        n = _parse_n(item)
        if n is not None:
            s = str(n)
            if s not in out:
                out.append(s)
    return out
