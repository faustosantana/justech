"""Multi-source failover + conflict detection for Lottery 3.0."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence


class _Cand(Protocol):
    source_id: int
    draw_date: Any
    numbers: list[str]
    source_reference: str | None


@dataclass
class SourceAttempt:
    source_key: str
    role: str  # primary | secondary | backup
    ok: bool
    latency_ms: float
    error: str | None = None
    candidates: int = 0


@dataclass
class SourceConflict:
    lottery_source_id: int
    draw_date: str
    field: str
    primary_value: Any
    other_value: Any
    other_source: str


@dataclass
class MultiSourceResult:
    chosen_source: str | None
    attempts: list[SourceAttempt] = field(default_factory=list)
    conflicts: list[SourceConflict] = field(default_factory=list)
    candidates: list[Any] = field(default_factory=list)
    blocked_write: bool = False
    block_reason: str | None = None


def _cand_key(c: Any) -> tuple:
    d = c.draw_date.isoformat() if hasattr(c.draw_date, "isoformat") else str(c.draw_date)
    return (c.source_id, d)


def compare_candidates(
    primary: Sequence[Any],
    other: Sequence[Any],
    *,
    other_source: str,
) -> list[SourceConflict]:
    """Compare overlapping draws; conflict if numbers/order/external_id differ."""
    conflicts: list[SourceConflict] = []
    other_map = {_cand_key(c): c for c in other}
    for p in primary:
        o = other_map.get(_cand_key(p))
        if not o:
            continue
        p_nums = list(getattr(p, "numbers", []) or [])
        o_nums = list(getattr(o, "numbers", []) or [])
        if len(p_nums) != len(o_nums):
            conflicts.append(
                SourceConflict(
                    lottery_source_id=p.source_id,
                    draw_date=str(p.draw_date),
                    field="numbers_count",
                    primary_value=len(p_nums),
                    other_value=len(o_nums),
                    other_source=other_source,
                )
            )
        elif p_nums != o_nums:
            conflicts.append(
                SourceConflict(
                    lottery_source_id=p.source_id,
                    draw_date=str(p.draw_date),
                    field="numbers_order",
                    primary_value=p_nums,
                    other_value=o_nums,
                    other_source=other_source,
                )
            )
        p_ext = getattr(p, "external_id", None) or getattr(p, "source_reference", None)
        o_ext = getattr(o, "external_id", None) or getattr(o, "source_reference", None)
        if p_ext and o_ext and str(p_ext) != str(o_ext):
            conflicts.append(
                SourceConflict(
                    lottery_source_id=p.source_id,
                    draw_date=str(p.draw_date),
                    field="external_id",
                    primary_value=p_ext,
                    other_value=o_ext,
                    other_source=other_source,
                )
            )
    return conflicts


def select_with_failover(
    attempts: list[tuple[str, str, list[Any] | Exception, float]],
) -> MultiSourceResult:
    """
    attempts: list of (source_key, role, candidates_or_exc, latency_ms)
    Prefer primary if healthy; else secondary; else backup.
    If primary and secondary both ok but conflict → block write.
    """
    result = MultiSourceResult(chosen_source=None)
    by_role: dict[str, tuple[str, list[Any], float]] = {}
    for key, role, payload, latency in attempts:
        if isinstance(payload, Exception):
            result.attempts.append(
                SourceAttempt(source_key=key, role=role, ok=False, latency_ms=latency, error=str(payload)[:500])
            )
            continue
        result.attempts.append(
            SourceAttempt(source_key=key, role=role, ok=True, latency_ms=latency, candidates=len(payload))
        )
        by_role[role] = (key, list(payload), latency)

    primary = by_role.get("primary")
    secondary = by_role.get("secondary")
    backup = by_role.get("backup")

    if primary and secondary:
        conflicts = compare_candidates(primary[1], secondary[1], other_source=secondary[0])
        if conflicts:
            result.conflicts = conflicts
            result.blocked_write = True
            result.block_reason = "source_conflict"
            result.candidates = primary[1]
            result.chosen_source = primary[0]
            return result

    for role in ("primary", "secondary", "backup"):
        row = by_role.get(role)
        if row:
            result.chosen_source = row[0]
            result.candidates = row[1]
            return result

    result.blocked_write = True
    result.block_reason = "all_sources_failed"
    return result


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
