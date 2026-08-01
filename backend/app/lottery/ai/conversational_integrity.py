"""Conversational integrity — explicit subjects override sticky inheritance / asset reuse.

Rule: if the current turn contains new explicit subjects, they replace inherited
subjects; prior investigation assets must not be reused unless subjects, relation,
and scope match exactly.
"""
from __future__ import annotations

from typing import Any, Sequence


def _norm(s: Any) -> str:
    t = str(s or "").strip()
    if t.isdigit():
        return t.zfill(2) if len(t) <= 2 else t
    return t


def normalize_subjects(subjects: Sequence[Any] | None, *, limit: int = 8) -> list[str]:
    out: list[str] = []
    for s in subjects or []:
        n = _norm(s)
        if n and n not in out:
            out.append(n)
        if len(out) >= limit:
            break
    return out


def explicit_subjects_override(
    message_subjects: Sequence[Any] | None,
    inherited_or_active: Sequence[Any] | None,
) -> list[str] | None:
    """Return current subjects when the message replaces sticky inheritance.

    Only applies when there is an active/inherited subject set to override.
    Fresh turns (no sticky subjects) leave routing to default research.

    - New pair ≠ active pair → pair wins.
    - Single subject not in active pair → individual wins.
    - Otherwise None (keep inheritance / contextual reuse).
    """
    msg = normalize_subjects(message_subjects, limit=8)
    active = normalize_subjects(inherited_or_active, limit=8)
    if not msg or not active:
        return None
    if len(msg) >= 2:
        if sorted(msg[:2]) != sorted(active[:2]):
            return msg[:2]
        return None
    if len(msg) == 1:
        if msg[0] not in set(active):
            return msg[:1]
        # Same subject already in active pair — not an override by itself
        # (use analyze-verb path for "Ahora analiza el 35" focus switch).
        return None
    return None


def asset_matches_current(
    asset: Any,
    *,
    subjects: Sequence[Any] | None,
    relation: str | None = None,
    scope: str | None = None,
) -> bool:
    """NO REUSE unless asset.subjects/relation/scope match the current intent."""
    if asset is None:
        return False
    want = normalize_subjects(subjects, limit=2)
    have = normalize_subjects(getattr(asset, "subjects", None), limit=2)
    if len(want) < 1 or sorted(want) != sorted(have):
        return False
    if relation:
        asset_rel = getattr(asset, "relation", None) or "same_day"
        if str(asset_rel) != str(relation):
            return False
    if scope:
        asset_scope = getattr(asset, "scope", None) or "official_seven"
        if str(asset_scope) != str(scope):
            return False
    return True
