"""Canonical response dimensions for Evidence Package / response_contract.

A dimension may be used in an answer only if its counts (or explicit rows)
appear in ``counts`` / authorized fields — never inferred from narrative alone.
"""

from __future__ import annotations

import re
from typing import Any

# Logical dimensions a response may claim with numbers
DIMENSIONS = (
    "total",
    "lottery",
    "position",
    "date",
    "subject",
    "frequency",
    "percentage",
    "ranking",
)

# Count keys that authorize a dimension when present in package.counts
_COUNT_KEY_DIMENSION: dict[str, str] = {
    "total": "total",
    "count": "total",
    "total_all_positions": "total",
    "first_related": "position",
    "both_first": "position",
    "other_only": "position",
}

_INFERENCE_FOR_DIMENSION: dict[str, str] = {
    "position": "position_breakdown",
    "lottery": "lottery_breakdown",
    "date": "date_breakdown",
    "subject": "subject_subtotals",
    "frequency": "frequency_breakdown",
    "percentage": "percentage_claims",
    "ranking": "ranking_without_totals",
}

# Narrative blocks that inject position subtotals into factual_answer templates
_POSITION_BREAKDOWN_BLOCK = re.compile(
    r"(?is)"
    r"(?:^|\n)\s*En\s+1ra\s+posici[oó]n:.*?"
    r"(?=(?:\n\s*En\s+otras\s+posiciones:)|\n\s*La\s+coincidencia\s+m[aá]s|\n\s*Interpretaci[oó]n:|\Z)"
)
_OTHER_POSITION_BLOCK = re.compile(
    r"(?is)"
    r"(?:"
    r"(?:^|\n)\s*En\s+otras\s+posiciones:.*?"
    r"(?=(?:\n\s*La\s+coincidencia\s+m[aá]s)|\n\s*Interpretaci[oó]n:|\Z)"
    r")"
)
_FILTERED_FIRST_LINE = re.compile(
    r"(?im)^En\s+1ra\s+posici[oó]n,\s+.+\d+\s+ocasi[oó]n.*$"
)


def allowed_counts_from_counts(counts: dict[str, Any] | None) -> list[int]:
    out: list[int] = []
    if not isinstance(counts, dict):
        return out
    for k, v in counts.items():
        if k.startswith("_"):
            continue
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if n not in out:
            out.append(n)
    return out


def allowed_dimensions_from_counts(counts: dict[str, Any] | None) -> list[str]:
    dims: list[str] = []
    if not isinstance(counts, dict):
        return dims
    for key, dim in _COUNT_KEY_DIMENSION.items():
        if counts.get(key) is None:
            continue
        if dim not in dims:
            dims.append(dim)
    # Explicit per-lottery / per-subject maps if ever present
    if any(str(k).startswith("by_lottery") for k in counts):
        if "lottery" not in dims:
            dims.append("lottery")
    if any(str(k).startswith("by_subject") for k in counts):
        if "subject" not in dims:
            dims.append("subject")
    return dims


def forbidden_inferences(allowed_dimensions: list[str]) -> list[str]:
    allowed = set(allowed_dimensions or [])
    out: list[str] = []
    for dim, label in _INFERENCE_FOR_DIMENSION.items():
        if dim not in allowed and label not in out:
            out.append(label)
    # Ranking / who-appears-more always forbidden unless subject dimension authorized
    if "subject" not in allowed and "subject_subtotals" not in out:
        out.append("subject_subtotals")
    if "ranking" not in allowed and "ranking_without_totals" not in out:
        out.append("ranking_without_totals")
    return out


def enrich_response_contract(
    contract: dict[str, Any] | None,
    *,
    counts: dict[str, Any] | None,
    resolved_intent: str | None = None,
    relation: str | None = None,
) -> dict[str, Any]:
    """Extend response_contract in-place-compatible copy (additive schema)."""
    out = dict(contract or {})
    dims = allowed_dimensions_from_counts(counts)
    allowed_counts = allowed_counts_from_counts(counts)
    out["allowed_dimensions"] = dims
    out["allowed_counts"] = allowed_counts
    out["forbidden_inferences"] = forbidden_inferences(dims)
    if "total" in dims and len(dims) == 1:
        op = "compare_same_day_total" if (relation == "same_day") else "report_canonical_total"
        out.setdefault("requested_operation", resolved_intent or op)
        if relation == "same_day":
            out["requested_operation"] = out.get("requested_operation") or op
            # Prefer explicit total-only op when only total is authorized
            if out.get("requested_operation") in {None, "", "new_investigation", "analysis"}:
                out["requested_operation"] = op
    total = None
    if isinstance(counts, dict) and counts.get("total") is not None:
        try:
            total = int(counts["total"])
        except (TypeError, ValueError):
            total = counts.get("total")
    if total is not None:
        out["canonical_count"] = total
    out.setdefault(
        "dimension_note",
        "Only dimensions listed in allowed_dimensions may carry numeric claims. "
        "Numbers not in allowed_counts are unauthorized unless taken from explicit authorized rows.",
    )
    return out


def sanitize_factual_answer_for_contract(
    factual_answer: str,
    counts: dict[str, Any] | None,
) -> str:
    """Remove narrative position breakdowns when those counts are not in package.counts."""
    text = (factual_answer or "").strip()
    if not text:
        return text
    dims = set(allowed_dimensions_from_counts(counts))
    if "position" in dims:
        return text
    text = _POSITION_BREAKDOWN_BLOCK.sub("\n", text)
    text = _OTHER_POSITION_BLOCK.sub("\n", text)
    text = _FILTERED_FIRST_LINE.sub("", text)
    # Drop template observation that pushes first-position preference
    text = re.sub(
        r"(?is)\n*Interpretaci[oó]n:\s*conviene mirar el total general y, por separado, "
        r"el recorte de primera posici[oó]n[^\n]*",
        "",
        text,
    )
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def text_has_unauthorized_breakdown(text: str, counts: dict[str, Any] | None) -> list[str]:
    """Return violation tags if text claims breakdowns not authorized by counts."""
    dims = set(allowed_dimensions_from_counts(counts))
    allowed = set(allowed_counts_from_counts(counts))
    violations: list[str] = []
    raw = text or ""

    if "position" not in dims:
        pos_claim = re.search(
            r"(?i)("
            r"\d{1,5}\s+casos?\s+en\s+primera\s+posici|"
            r"ambos\s+(?:salieron|coincidieron)\s+en\s+primera\s+posici|"
            r"en\s+1ra\s+posici[oó]n|"
            r"primera\s+posici[oó]n\s+(?:frente|en)\s+\d|"
            r"\d{1,5}\s+ocasiones?\s+en\s+(?:1ra|primera)"
            r")",
            raw,
        )
        if pos_claim:
            # Allow qualitative "sin desglose de posición"
            if not re.search(
                r"(?i)(no\s+(?:hay|incluye|proporciona|contiene)\s+(?:un\s+)?desglose|"
                r"sin\s+desglose|no\s+se\s+puede\s+(?:afirmar|determinar))",
                raw[max(0, pos_claim.start() - 80) : pos_claim.end() + 80],
            ):
                violations.append("unauthorized_breakdown:position")

    if "subject" not in dims and "ranking" not in dims:
        ranking_claim = re.search(
            r"(?i)("
            r"(?:el\s+n[uú]mero\s+\d{1,2}\s+)?aparece\s+m[aá]s|"
            r"tiene\s+mayor\s+presencia|"
            r"ganador\s+hist[oó]rico"
            r")",
            raw,
        )
        if ranking_claim:
            # OK if the claim is framed as impossible / missing breakdown
            if not re.search(
                r"(?i)("
                r"no\s+es\s+posible\s+determinar|"
                r"no\s+se\s+puede\s+(?:afirmar|determinar|responder)|"
                r"no\s+(?:hay|incluye|contiene|proporciona)\s+(?:un\s+)?desglose|"
                r"evidencia\s+(?:entregada\s+)?no\s+(?:incluye|contiene|proporciona)|"
                r"permita\s+determinar|"
                r"sin\s+desglose|"
                r"solo\s+(?:hay|expresa)\s+total"
                r")",
                raw,
            ):
                violations.append("unauthorized_breakdown:subject_ranking")

    # Numeric claims equal to neither canonical total nor allowed_counts (coarse)
    total = None
    if isinstance(counts, dict) and counts.get("total") is not None:
        try:
            total = int(counts["total"])
        except (TypeError, ValueError):
            total = None
    if total is not None and "position" not in dims:
        for m in re.finditer(
            r"\b(\d{1,5})\s+(?:casos?|ocasiones?|veces)\b",
            raw,
            re.I,
        ):
            n = int(m.group(1))
            if n in allowed or n in {1, 2, 3, 7}:
                continue
            span = raw[max(0, m.start() - 40) : m.end() + 40]
            if re.search(r"(?i)primera\s+posici|1ra\s+posici|ambos\s+en\s+primera", span):
                violations.append(f"unauthorized_breakdown:count:{n}")
    # dedupe
    seen: set[str] = set()
    out: list[str] = []
    for v in violations:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out
