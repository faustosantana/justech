"""Input normalization for Complete Analysis Engine."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.lottery.numeric_relations.constants import N_MAX, N_MIN
from app.lottery.numeric_relations.analysis_engine.schemas import (
    AnalysisRequest,
    InputMode,
    RankProfile,
)


def normalize_number(n: int) -> int:
    v = int(n)
    if not (N_MIN <= v <= N_MAX):
        raise ValueError(f"number {v} outside range {N_MIN}..{N_MAX}")
    return v


def normalize_positions(positions: list[str] | None) -> list[str]:
    """Default: primera posición. Never silently mix positions."""
    if not positions:
        return ["first"]
    out: list[str] = []
    for p in positions:
        key = str(p).strip().lower()
        if key in {"1", "first", "primera", "pos1", "position_1"}:
            out.append("first")
        elif key in {"2", "second", "segunda", "pos2", "position_2"}:
            out.append("second")
        elif key in {"3", "third", "tercera", "pos3", "position_3"}:
            out.append("third")
        else:
            raise ValueError(f"unsupported position label: {p}")
    # preserve order, unique
    seen: set[str] = set()
    uniq: list[str] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def normalize_mode(mode: str | None) -> str:
    if not mode:
        return RankProfile.MANUAL_RECONSTRUCTED.value
    m = str(mode).strip().lower()
    aliases = {
        "strict": RankProfile.STRICT.value,
        "estricto": RankProfile.STRICT.value,
        "amplio": RankProfile.BROAD.value,
        "broad": RankProfile.BROAD.value,
        "manual": RankProfile.MANUAL_RECONSTRUCTED.value,
        "manual_reconstruido": RankProfile.MANUAL_RECONSTRUCTED.value,
        "perfil_manual": RankProfile.MANUAL_RECONSTRUCTED.value,
        "experimental": RankProfile.EXPERIMENTAL.value,
    }
    if m not in aliases and m not in {e.value for e in RankProfile}:
        raise ValueError(f"unsupported rank profile: {mode}")
    return aliases.get(m, m)


def normalize_request(raw: AnalysisRequest | dict[str, Any]) -> AnalysisRequest:
    if isinstance(raw, AnalysisRequest):
        req = raw
    else:
        nums = raw.get("numbers") or raw.get("observed_numbers") or []
        d = raw.get("date")
        if isinstance(d, str) and d:
            d = date.fromisoformat(d[:10])
        req = AnalysisRequest(
            numbers=list(nums),
            date=d,
            positions=list(raw.get("positions") or ["first"]),
            mode=str(raw.get("mode") or RankProfile.MANUAL_RECONSTRUCTED.value),
            derivation_depth=int(raw.get("derivation_depth") or 2),
            historical_window_years=int(raw.get("historical_window_years") or 7),
            lotteries=list(raw.get("lotteries") or []),
            input_mode=str(raw.get("input_mode") or InputMode.MANUAL.value),
            create_signals=bool(raw.get("create_signals", True)),
            explanation_level=str(raw.get("explanation_level") or "analitico"),
        )

    if not req.numbers:
        raise ValueError("at least one observed number is required")

    # Preserve duplicates as multiplicity signal but analyze unique set;
    # keep original order for traceability.
    normalized_nums = [normalize_number(n) for n in req.numbers]
    depth = max(0, min(int(req.derivation_depth), 2))
    return AnalysisRequest(
        numbers=normalized_nums,
        date=req.date,
        positions=normalize_positions(req.positions),
        mode=normalize_mode(req.mode),
        derivation_depth=depth,
        historical_window_years=max(1, int(req.historical_window_years)),
        lotteries=list(req.lotteries or []),
        input_mode=req.input_mode or InputMode.MANUAL.value,
        create_signals=bool(req.create_signals),
        explanation_level=req.explanation_level,
    )


def unique_observed(numbers: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for n in numbers:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out
