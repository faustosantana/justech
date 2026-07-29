"""Apply filter / sort / paginate on InvestigationAsset (in-memory)."""

from __future__ import annotations

import re
from typing import Any

from app.lottery.ai.investigation_workspace.schemas import (
    AssetFilters,
    AssetPagination,
    AssetSort,
    InvestigationAsset,
)
from app.lottery.ai.official_lottery_scope import (
    canonicalize_lottery_name,
    is_official_lottery,
)


def lottery_canonical_key(name: str | None) -> str | None:
    """Stable key for filter comparisons (accent/case/alias insensitive)."""
    canon = canonicalize_lottery_name(name)
    if not canon:
        raw = (name or "").strip()
        if not raw:
            return None
        # Fallback: NFKD fold without requiring official membership
        import unicodedata

        nfkd = unicodedata.normalize("NFKD", raw.lower())
        bare = "".join(c for c in nfkd if not unicodedata.combining(c))
        return re.sub(r"\s+", " ", bare).strip() or None
    import unicodedata

    nfkd = unicodedata.normalize("NFKD", canon.lower())
    bare = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", bare).strip() or None


def _lot_match(row_lot: str, wanted: str) -> bool:
    """Match lottery labels by canonical key, not fragile display strings."""
    if not wanted:
        return True
    key_row = lottery_canonical_key(row_lot)
    key_want = lottery_canonical_key(wanted)
    if key_row and key_want and key_row == key_want:
        return True
    # Substring fallback for partial labels already canonicalized
    a = key_row or ""
    b = key_want or ""
    if not a or not b:
        return False
    if b in a or a in b:
        return True
    return b.replace("quiniela ", "") in a or a.replace("quiniela ", "") in b


def apply_filters(rows: list[dict[str, Any]], filters: AssetFilters) -> list[dict[str, Any]]:
    out = list(rows)
    if filters.lottery:
        out = [
            r
            for r in out
            if _lot_match(str(r.get("loteria") or ""), filters.lottery)
            or _lot_match(str(r.get("loteria_a") or ""), filters.lottery)
            or _lot_match(str(r.get("loteria_b") or ""), filters.lottery)
        ]
    if filters.date_from:
        out = [r for r in out if str(r.get("fecha") or "") >= filters.date_from]
    if filters.date_to:
        out = [r for r in out if str(r.get("fecha") or "") <= filters.date_to]
    if filters.position is not None:
        p = int(filters.position)
        out = [
            r
            for r in out
            if r.get("posicion_a_num") == p or r.get("posicion_b_num") == p
        ]
    if filters.number:
        n = str(filters.number).zfill(2)
        out = [
            r
            for r in out
            if str(r.get("numero_a") or "").zfill(2) == n
            or str(r.get("numero_b") or "").zfill(2) == n
        ]
    if filters.same_lottery is True:
        out = [r for r in out if r.get("tipo_coincidencia") in {"misma_loteria", "misma_loteria_y_posicion"}]
    if filters.same_position is True:
        out = [
            r
            for r in out
            if r.get("posicion_a_num") is not None
            and r.get("posicion_a_num") == r.get("posicion_b_num")
        ]
    if filters.limit is not None:
        out = out[: max(0, int(filters.limit))]
    # Safety: never surface non-official lottery labels
    cleaned = []
    for r in out:
        lot = str(r.get("loteria") or "")
        if lot and not is_official_lottery(lot):
            continue
        cleaned.append(r)
    return cleaned


def apply_sort(rows: list[dict[str, Any]], sort: AssetSort) -> list[dict[str, Any]]:
    field = sort.field or "fecha"
    reverse = (sort.direction or "desc").lower() != "asc"

    def key(r: dict[str, Any]) -> Any:
        v = r.get(field)
        if v is None and field == "fecha":
            v = ""
        if field.endswith("_num"):
            return v if isinstance(v, (int, float)) else -1
        return str(v or "")

    return sorted(rows, key=key, reverse=reverse)


def recompute_view(asset: InvestigationAsset) -> InvestigationAsset:
    rows = apply_filters(list(asset.source_rows or []), asset.filters)
    rows = apply_sort(rows, asset.sort)
    asset.rows = rows
    asset.row_count = len(rows)
    # Clamp page
    total_pages = max(
        1,
        (asset.row_count + asset.pagination.page_size - 1)
        // max(1, asset.pagination.page_size),
    )
    if asset.pagination.page > total_pages:
        asset.pagination.page = total_pages
    asset.touch()
    return asset


def set_filters(asset: InvestigationAsset, filters: AssetFilters) -> InvestigationAsset:
    asset.filters = filters
    asset.pagination.page = 1
    return recompute_view(asset)


def set_sort(asset: InvestigationAsset, sort: AssetSort) -> InvestigationAsset:
    asset.sort = sort
    asset.pagination.page = 1
    return recompute_view(asset)


def set_pagination(asset: InvestigationAsset, pagination: AssetPagination) -> InvestigationAsset:
    asset.pagination = pagination
    return recompute_view(asset)
