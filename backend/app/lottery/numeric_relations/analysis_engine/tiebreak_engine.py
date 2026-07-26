"""Tiebreak Engine — reorder already-ranked candidates; never rediscover."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.lottery.numeric_relations.analysis_engine.schemas import (
    Classification,
    RankedCandidate,
)

TIEBREAK_ENGINE_VERSION = "tiebreak-engine-j1.0.0"

# Selected after train/val exploration (test locked during selection).
SELECTED_RULE_ID = "TIEBREAK_PROFILE_SOCIO_V1"
DEFAULT_PRACTICAL_THRESHOLD = 0.0  # all 14 Phase-2 errors were exact score ties


@dataclass
class TiebreakDecision:
    number: int
    original_rank: int
    final_rank: int
    score_before: float
    score_after: float
    tiebreak_triggered: bool
    tiebreak_rule: str | None
    tiebreak_evidence: dict[str, Any]
    candidates_compared: list[int]
    decision_margin: float
    tie_status: str
    unresolved_tie: bool
    shared_rank: int | None
    classification: str
    engine_version: str = TIEBREAK_ENGINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _score(c: RankedCandidate | dict[str, Any]) -> float:
    if isinstance(c, RankedCandidate):
        return float(c.total_score)
    return float(c.get("total_score") or c.get("score") or 0.0)


def _num(c: RankedCandidate | dict[str, Any]) -> int:
    return int(c.number if isinstance(c, RankedCandidate) else c["number"])


def _ev(c: RankedCandidate | dict[str, Any]) -> dict[str, Any]:
    if isinstance(c, RankedCandidate):
        return c.evidence.to_dict()
    return c.get("evidence") or {}


def _cls(c: RankedCandidate | dict[str, Any]) -> str:
    return c.classification if isinstance(c, RankedCandidate) else str(c.get("classification"))


def is_officialish(c: RankedCandidate | dict[str, Any]) -> bool:
    return _cls(c) in {
        Classification.FUERTE_PRINCIPAL.value,
        Classification.FUERTE_SECUNDARIO.value,
        Classification.CANDIDATO_CONFIRMADO.value,
        "EMPATE_MULTI_FUERTE",
    } or bool((_ev(c).get("cross_table_support")))


def detect_tie_group(
    ranked: list[RankedCandidate] | list[dict[str, Any]],
    *,
    practical_threshold: float = DEFAULT_PRACTICAL_THRESHOLD,
) -> tuple[list[Any], str]:
    """Return leading tie group and tie kind (none|real|practical)."""
    if len(ranked) < 2:
        return list(ranked[:1]), "none"
    top = [c for c in ranked if is_officialish(c)] or list(ranked)
    if len(top) < 2:
        return top[:1], "none"
    s0 = _score(top[0])
    group = [top[0]]
    kind = "none"
    for c in top[1:]:
        gap = abs(s0 - _score(c))
        if gap <= 1e-9:
            group.append(c)
            kind = "real"
        elif gap <= practical_threshold:
            group.append(c)
            kind = "practical" if kind == "none" else kind
        else:
            break
    if len(group) < 2:
        return group, "none"
    return group, kind


def hypothesis_key(
    name: str,
    c: RankedCandidate | dict[str, Any],
    *,
    observed_numbers: list[int],
) -> tuple:
    """Lower tuple wins. Structural only — no future labels."""
    ev = _ev(c)
    t1 = list(ev.get("table1_sources") or [])
    t2 = list(ev.get("direct_confirmers") or [])
    first = observed_numbers[0] if observed_numbers else None
    indep_sources = len(set(t1) | set(t2))
    cross = 1 if ev.get("cross_table_support") else 0
    depth = float(ev.get("derivation_paths") and min(
        (p.get("depth", 2) for p in (ev.get("derivation_paths") or [])), default=0
    ) or 0)
    # components may carry depth penalty already
    dup = float(ev.get("same_source_repetitions") or 0)
    hist_exact = float(ev.get("historical_exact_hits") or 0)
    d1d3 = float(
        (ev.get("d1_hits") or 0) + (ev.get("d2_hits") or 0) + (ev.get("d3_hits") or 0)
    )
    first_pos = float(ev.get("historical_first_position_hits") or 0)
    recent = float(len(ev.get("recent_equivalent_cases") or []))
    repeated_input_boost = 0
    # repeated inputs in observed list
    if observed_numbers:
        from collections import Counter

        cnt = Counter(observed_numbers)
        repeated_input_boost = -sum(
            cnt[x] - 1 for x in t1 if cnt.get(x, 0) > 1
        )  # more repeats → lower key

    if name == "TIEBREAK_MORE_INDEPENDENT_SOURCES":
        return (-indep_sources, _num(c))
    if name == "TIEBREAK_STRONGER_CROSS_TABLE":
        return (-cross, -len(t1), -len(t2), _num(c))
    if name == "TIEBREAK_MORE_DIRECT_T2_CONFIRMERS":
        return (-len(t2), _num(c))
    if name == "TIEBREAK_MORE_DIRECT_T1_SOURCES":
        return (-len(t1), _num(c))
    if name == "TIEBREAK_LOWER_DEPTH":
        return (depth, _num(c))
    if name == "TIEBREAK_FEWER_DUPLICATE_PATHS":
        return (dup, _num(c))
    if name == "TIEBREAK_FIRST_POSITION_SUPPORT":
        return (-first_pos, _num(c))
    if name == "TIEBREAK_SHORT_WINDOW_HISTORY":
        return (-d1d3, _num(c))
    if name == "TIEBREAK_EXACT_HISTORY":
        return (-hist_exact, _num(c))
    if name == "TIEBREAK_RECENT_EQUIVALENT_CASES":
        return (-recent, _num(c))
    if name == "TIEBREAK_SOURCE_ORDER":
        # Prefer T1 support from first observed (generator hint when caller orders origin first)
        prefer = 0 if (first is not None and first in t1) else 1
        return (prefer, _num(c))
    if name == "TIEBREAK_REPEATED_INPUT":
        return (repeated_input_boost, _num(c))
    if name == "TIEBREAK_PROFILE_SOCIO":
        # Hierarchical socio reconstruction (validated on train/val):
        # 1) prefer generator hint (first observed) as T1 source
        # 2) more independent observed supports
        # 3) more direct T2 confirmers
        # 4) more direct T1 sources
        # 5) stronger cross flag
        # Remaining exact ties → EMPATE_MULTI_FUERTE (no lexicographic number / path-count bias)
        prefer = 0 if (first is not None and first in t1) else 1
        return (
            prefer,
            -indep_sources,
            -len(t2),
            -len(t1),
            -cross,
        )
    # baseline: preserve incoming order (stable)
    return (0,)


def apply_hypothesis(
    ranked: list[RankedCandidate] | list[dict[str, Any]],
    *,
    hypothesis: str,
    observed_numbers: list[int],
    practical_threshold: float = DEFAULT_PRACTICAL_THRESHOLD,
    allow_multi_fuerte: bool = False,
) -> tuple[list[Any], list[TiebreakDecision]]:
    """
    Reorder leading tie group by hypothesis. Preserves original scores.
    If allow_multi_fuerte and PROFILE_SOCIO still ties, mark EMPATE_MULTI_FUERTE.
    """
    if not ranked:
        return [], []
    # work on shallow copies of dicts for uniformity
    items: list[Any] = list(ranked)
    group, kind = detect_tie_group(items, practical_threshold=practical_threshold)
    decisions: list[TiebreakDecision] = []

    if kind == "none" or len(group) < 2:
        for i, c in enumerate(items, start=1):
            decisions.append(
                TiebreakDecision(
                    number=_num(c),
                    original_rank=i,
                    final_rank=i,
                    score_before=_score(c),
                    score_after=_score(c),
                    tiebreak_triggered=False,
                    tiebreak_rule=None,
                    tiebreak_evidence={"tie_kind": kind},
                    candidates_compared=[_num(x) for x in group],
                    decision_margin=0.0,
                    tie_status="none",
                    unresolved_tie=False,
                    shared_rank=None,
                    classification=_cls(c),
                )
            )
        return items, decisions

    original_index = {_num(c): i + 1 for i, c in enumerate(items)}
    compared = [_num(c) for c in group]
    keyed = sorted(
        group, key=lambda c: hypothesis_key(hypothesis, c, observed_numbers=observed_numbers)
    )

    unresolved = False
    if hypothesis == "TIEBREAK_PROFILE_SOCIO" and allow_multi_fuerte:
        k0 = hypothesis_key(hypothesis, keyed[0], observed_numbers=observed_numbers)
        still = [
            c
            for c in keyed
            if hypothesis_key(hypothesis, c, observed_numbers=observed_numbers) == k0
        ]
        if len(still) > 1:
            unresolved = True
            keyed = still + [c for c in keyed if c not in still]

    # Rebuild list: tied group first in new order, then the rest
    group_nums = {_num(c) for c in group}
    rest = [c for c in items if _num(c) not in group_nums]
    new_order = list(keyed) + rest

    # Assign classifications
    if unresolved:
        shared = 1
        for c in keyed:
            if isinstance(c, RankedCandidate):
                c.classification = "EMPATE_MULTI_FUERTE"
                c.classification_reason = (
                    "Empate estructural no resuelto tras TIEBREAK_PROFILE_SOCIO; "
                    "no se finge un único fuerte."
                )
            elif isinstance(c, dict):
                c["classification"] = "EMPATE_MULTI_FUERTE"
                c["classification_reason"] = (
                    "Empate estructural no resuelto tras TIEBREAK_PROFILE_SOCIO; "
                    "no se finge un único fuerte."
                )
        # demote others
        for i, c in enumerate(new_order):
            n = _num(c)
            if n in {_num(x) for x in keyed}:
                final_rank = shared
                tie_status = "unresolved_multi"
                rule = SELECTED_RULE_ID
                unc = True
                sh = shared
                cls = "EMPATE_MULTI_FUERTE"
            else:
                # shift ranks after multi block
                final_rank = i + 1
                tie_status = kind
                rule = hypothesis
                unc = False
                sh = None
                cls = _cls(c)
            decisions.append(
                TiebreakDecision(
                    number=n,
                    original_rank=original_index[n],
                    final_rank=final_rank,
                    score_before=_score(c),
                    score_after=_score(c),
                    tiebreak_triggered=True,
                    tiebreak_rule=rule,
                    tiebreak_evidence={
                        "tie_kind": kind,
                        "hypothesis": hypothesis,
                        "key": list(
                            hypothesis_key(hypothesis, c, observed_numbers=observed_numbers)
                        ),
                        "threshold": practical_threshold,
                    },
                    candidates_compared=compared,
                    decision_margin=0.0,
                    tie_status=tie_status,
                    unresolved_tie=unc,
                    shared_rank=sh,
                    classification=cls,
                )
            )
    else:
        # Winner is first; update classifications for RankedCandidate objects
        for i, c in enumerate(new_order):
            n = _num(c)
            if i == 0 and is_officialish(c):
                if isinstance(c, RankedCandidate):
                    c.classification = Classification.FUERTE_PRINCIPAL.value
                    c.rank = 1
                elif isinstance(c, dict):
                    c["classification"] = Classification.FUERTE_PRINCIPAL.value
                    c["rank"] = 1
            elif i == 1 and is_officialish(c) and abs(_score(new_order[0]) - _score(c)) <= max(
                practical_threshold, 1e-9
            ):
                if isinstance(c, RankedCandidate):
                    c.classification = Classification.FUERTE_SECUNDARIO.value
                    c.rank = 2
                elif isinstance(c, dict):
                    c["classification"] = Classification.FUERTE_SECUNDARIO.value
                    c["rank"] = 2
            decisions.append(
                TiebreakDecision(
                    number=n,
                    original_rank=original_index[n],
                    final_rank=i + 1,
                    score_before=_score(c),
                    score_after=_score(c),
                    tiebreak_triggered=(n in group_nums),
                    tiebreak_rule=hypothesis if n in group_nums else None,
                    tiebreak_evidence={
                        "tie_kind": kind,
                        "hypothesis": hypothesis,
                        "threshold": practical_threshold,
                    },
                    candidates_compared=compared,
                    decision_margin=abs(_score(new_order[0]) - _score(c)) if i > 0 else 0.0,
                    tie_status=kind if n in group_nums else "none",
                    unresolved_tie=False,
                    shared_rank=None,
                    classification=_cls(c),
                )
            )
        # refresh ranks
        for i, c in enumerate(new_order, start=1):
            if isinstance(c, RankedCandidate):
                c.rank = i
            elif isinstance(c, dict):
                c["rank"] = i

    return new_order, decisions


def apply_selected_tiebreak(
    ranked: list[RankedCandidate],
    *,
    observed_numbers: list[int],
    practical_threshold: float = DEFAULT_PRACTICAL_THRESHOLD,
    enable: bool = True,
) -> tuple[list[RankedCandidate], list[TiebreakDecision]]:
    if not enable or not ranked:
        return ranked, []
    ordered, decisions = apply_hypothesis(
        ranked,
        hypothesis="TIEBREAK_PROFILE_SOCIO",
        observed_numbers=observed_numbers,
        practical_threshold=practical_threshold,
        allow_multi_fuerte=True,
    )
    # ensure list type RankedCandidate
    return list(ordered), decisions
