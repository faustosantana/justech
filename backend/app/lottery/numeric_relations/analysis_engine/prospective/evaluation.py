"""Evaluation rules for locked prospective predictions (D+1 … D+7)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any


EVAL_CLASSES = {
    "EXACT_PRIMARY_HIT",
    "EXACT_MULTI_STRONG_HIT",
    "EXACT_TOP2_HIT",
    "EXACT_TOP3_HIT",
    "T1_FAMILY_HIT",
    "T2_NEIGHBOR_HIT",
    "NO_HIT",
    "PARTIAL_RESULT",
    "INVALID_RESULT",
    "INTEGRITY_ERROR",
}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def relative_day(analysis_or_target: str | None, result_date: str | None) -> int | None:
    a = _parse_date(analysis_or_target)
    b = _parse_date(result_date)
    if a is None or b is None:
        return None
    return (b - a).days


def classify_hit(
    *,
    drawn: list[int],
    primary: int | None,
    multi: list[int],
    top2: list[int],
    top3: list[int],
    t1_family: list[int] | None = None,
    t2_neighbors: list[int] | None = None,
    integrity_ok: bool = True,
) -> str:
    if not integrity_ok:
        return "INTEGRITY_ERROR"
    if not drawn:
        return "INVALID_RESULT"
    drawn_set = set(drawn)
    if multi and any(n in drawn_set for n in multi):
        return "EXACT_MULTI_STRONG_HIT"
    if primary is not None and primary in drawn_set and not multi:
        return "EXACT_PRIMARY_HIT"
    if any(n in drawn_set for n in top2):
        return "EXACT_TOP2_HIT"
    if any(n in drawn_set for n in top3):
        return "EXACT_TOP3_HIT"
    if t1_family and any(n in drawn_set for n in t1_family):
        return "T1_FAMILY_HIT"
    if t2_neighbors and any(n in drawn_set for n in t2_neighbors):
        return "T2_NEIGHBOR_HIT"
    return "NO_HIT"


def build_dn_map(
    *,
    base_date: str | None,
    appearances: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group appearances by D+n for n=1..7."""
    out = {f"D+{n}": [] for n in range(1, 8)}
    for app in appearances:
        rd = relative_day(base_date, app.get("date"))
        if rd is None or rd < 1 or rd > 7:
            continue
        out[f"D+{rd}"].append(app)
    return out


def evaluate_locked_prediction(
    pred: dict[str, Any],
    future_result: dict[str, Any],
    *,
    integrity_ok: bool = True,
) -> dict[str, Any]:
    drawn = [int(x) for x in (future_result.get("numbers") or [])]
    ranking = pred.get("ranking") or []
    multi = list(pred.get("multi_strong_candidates") or [])
    if not multi:
        multi = list((pred.get("tiebreak") or {}).get("multi_fuerte_numbers") or [])
    primary = None
    if not multi and ranking:
        primary = ranking[0].get("number")
    elif pred.get("primary_signal") and not multi:
        primary = (pred.get("primary_signal") or {}).get("number")
    top_nums = [r.get("number") for r in ranking if r.get("number") is not None]
    top2 = top_nums[:2] if not multi else list(multi)[:2]
    top3 = top_nums[:3] if not multi else list(dict.fromkeys(list(multi) + top_nums))[:3]

    # Family / neighbor from candidates classifications (not exact)
    t1_family = [
        c.get("number")
        for c in (pred.get("candidates") or [])
        if str(c.get("classification") or "").startswith("FAMILIA_T1")
    ]
    t2_neighbors = [
        c.get("number")
        for c in (pred.get("candidates") or [])
        if "VECINO_T2" in str(c.get("classification") or "")
    ]

    hit_class = classify_hit(
        drawn=drawn,
        primary=primary,
        multi=multi,
        top2=[n for n in top2 if n is not None],
        top3=[n for n in top3 if n is not None],
        t1_family=[n for n in t1_family if n is not None],
        t2_neighbors=[n for n in t2_neighbors if n is not None],
        integrity_ok=integrity_ok,
    )

    result_date = future_result.get("date")
    base = pred.get("target_date") or pred.get("analysis_date")
    dn = relative_day(base, result_date)
    appearance = {
        "date": result_date,
        "lottery": future_result.get("lottery"),
        "position": future_result.get("position"),
        "numbers": drawn,
        "relative_day": dn,
        "hit_class": hit_class,
    }
    dn_map = build_dn_map(base_date=base, appearances=[appearance])

    exact_primary = hit_class == "EXACT_PRIMARY_HIT"
    exact_multi = hit_class == "EXACT_MULTI_STRONG_HIT"
    exact_top2 = hit_class in {
        "EXACT_PRIMARY_HIT",
        "EXACT_MULTI_STRONG_HIT",
        "EXACT_TOP2_HIT",
    }
    exact_top3 = exact_top2 or hit_class == "EXACT_TOP3_HIT"

    return {
        "hit_class": hit_class,
        "hit_primary_exact": exact_primary,
        "hit_multi_fuerte": exact_multi,
        "hit_top2_exact": exact_top2,
        "hit_top3_exact": exact_top3,
        "is_exact_hit": exact_primary or exact_multi,
        "is_t1_family_only": hit_class == "T1_FAMILY_HIT",
        "is_t2_neighbor_only": hit_class == "T2_NEIGHBOR_HIT",
        "drawn_numbers": drawn,
        "relative_day": dn,
        "d_plus": dn_map,
        "first_appearance": appearance if dn and 1 <= dn <= 7 else None,
        "case_closed": exact_primary or exact_multi,  # exact-only close rule
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "integrity_ok": integrity_ok,
    }
