"""Materialize InvestigationAsset rows from same-day coincidence payloads."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.lottery.ai.investigation_workspace.schemas import (
    SAME_DAY_COLUMNS,
    InvestigationAsset,
)
from app.lottery.ai.official_lottery_scope import is_official_lottery, scope_label_es
from app.lottery.ai.turn_policy import position_label_es


def _norm_num(n: Any) -> str:
    s = str(n or "").strip()
    if s.isdigit() and len(s) <= 2:
        return s.zfill(2)
    return s


def coincidence_item_to_rows(
    item: dict[str, Any],
    *,
    subjects: list[str],
) -> list[dict[str, Any]]:
    """One coincidence date → one flat row (pair-centric)."""
    if not isinstance(item, dict):
        return []
    date_s = str(item.get("date") or item.get("draw_date") or "")[:10]
    appearances = list(item.get("appearances") or item.get("entries") or [])
    by_num: dict[str, list[dict[str, Any]]] = {}
    for e in appearances:
        if not isinstance(e, dict):
            continue
        lot = str(e.get("lottery") or "")
        if lot and not is_official_lottery(lot):
            continue
        n = _norm_num(e.get("number"))
        by_num.setdefault(n, []).append(e)

    a = _norm_num(subjects[0]) if subjects else ""
    b = _norm_num(subjects[1]) if len(subjects) > 1 else ""
    ea = (by_num.get(a) or [None])[0]
    eb = (by_num.get(b) or [None])[0]
    if not ea and not eb and appearances:
        # fallback: first two appearances
        ea = appearances[0] if appearances else None
        eb = appearances[1] if len(appearances) > 1 else None
        a = _norm_num((ea or {}).get("number")) if ea else a
        b = _norm_num((eb or {}).get("number")) if eb else b

    lot_a = str((ea or {}).get("lottery") or "")
    lot_b = str((eb or {}).get("lottery") or "")
    pos_a = (ea or {}).get("position")
    pos_b = (eb or {}).get("position")
    same_lot = bool(lot_a and lot_b and lot_a == lot_b)
    same_pos = (
        pos_a is not None
        and pos_b is not None
        and int(pos_a) == int(pos_b)
    )
    if same_lot and same_pos:
        tipo = "misma_loteria_y_posicion"
    elif same_lot:
        tipo = "misma_loteria"
    else:
        tipo = "misma_fecha"

    # Primary lottery column: prefer shared, else A then B
    loteria = lot_a if same_lot else (lot_a or lot_b or str(item.get("lottery") or ""))

    return [
        {
            "fecha": date_s,
            "loteria": loteria,
            "loteria_a": lot_a,
            "loteria_b": lot_b,
            "numero_a": a,
            "posicion_a": position_label_es((ea or {}).get("position_label") or pos_a)
            if ea
            else "",
            "posicion_a_num": int(pos_a) if pos_a is not None else None,
            "numero_b": b,
            "posicion_b": position_label_es((eb or {}).get("position_label") or pos_b)
            if eb
            else "",
            "posicion_b_num": int(pos_b) if pos_b is not None else None,
            "tipo_coincidencia": tipo,
        }
    ]


def materialize_same_day_table(
    *,
    items: list[dict[str, Any]],
    subjects: list[str],
    total: int | None = None,
    investigation_id: str | None = None,
    conversation_id: str | None = None,
    title: str | None = None,
) -> InvestigationAsset:
    subjects_n = [_norm_num(s) for s in subjects if str(s).strip()][:2]
    rows: list[dict[str, Any]] = []
    for it in items:
        rows.extend(coincidence_item_to_rows(it, subjects=subjects_n))

    # Stable hash of source
    raw = json.dumps(
        {"subjects": subjects_n, "n": len(rows), "dates": [r.get("fecha") for r in rows[:5]]},
        sort_keys=True,
        ensure_ascii=False,
    )
    qhash = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    label = " y ".join(subjects_n) if subjects_n else "números"
    asset = InvestigationAsset(
        investigation_id=investigation_id,
        conversation_id=conversation_id,
        asset_type="result_table",
        title=title or f"Coincidencias same-day: {label}",
        subjects=subjects_n,
        relation="same_day",
        scope="official_seven",
        columns=list(SAME_DAY_COLUMNS),
        source_rows=rows,
        rows=list(rows),
        row_count=len(rows),
        source_query_hash=qhash,
        evidence_hash=qhash,
    )
    # Prefer declared SQL total when items truncated — still store what we have
    if total is not None and int(total) > len(rows):
        # Keep factual total visible via title note; rows are what we have
        asset.title = (
            f"Coincidencias same-day: {label} "
            f"({len(rows)} filas materializadas / total declarado {int(total)}; "
            f"{scope_label_es()})"
        )
    return asset


async def materialize_same_day_from_query(
    query_service: Any,
    *,
    subjects: list[str],
    lotteries: list[str] | None = None,
    investigation_id: str | None = None,
    conversation_id: str | None = None,
    limit_dates: int = 500,
) -> InvestigationAsset:
    """Re-query SQL for full operable rows (official scope)."""
    payload = await query_service.same_day_number_coincidences(
        list(subjects)[:2],
        lotteries=lotteries,
        position=None,
        limit_dates=limit_dates,
        also_all_positions_totals=False,
    )
    items = list(payload.get("items") or [])
    total = int(payload.get("total") if payload.get("total") is not None else len(items))
    return materialize_same_day_table(
        items=items,
        subjects=list(subjects)[:2],
        total=total,
        investigation_id=investigation_id,
        conversation_id=conversation_id,
    )
