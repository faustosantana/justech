"""Modelos de dominio — eventos, ventanas, posterior, tasas (sin ORM)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from app.lottery.numeric_relations.historical.enums import (
    ConfirmationWindowMode,
    Horizon,
    SampleTier,
    SessionBucket,
)
from app.lottery.numeric_relations.historical.version import METHODOLOGY_VERSION


@dataclass(frozen=True)
class ConfirmationWindowConfig:
    mode: ConfirmationWindowMode
    timezone: str = "America/Santo_Domingo"
    hours_after: int | None = None  # for HOURS_AFTER
    next_k: int | None = None  # for NEXT_K_DRAWS
    session: SessionBucket | None = None  # optional filter for SAME_SESSION

    def __post_init__(self) -> None:
        if self.mode == ConfirmationWindowMode.HOURS_AFTER:
            if self.hours_after is None or int(self.hours_after) < 1:
                raise ValueError("HOURS_AFTER requires hours_after >= 1")
        if self.mode == ConfirmationWindowMode.NEXT_K_DRAWS:
            if self.next_k is None or int(self.next_k) < 1:
                raise ValueError("NEXT_K_DRAWS requires next_k >= 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "timezone": self.timezone,
            "hours_after": self.hours_after,
            "next_k": self.next_k,
            "session": self.session.value if self.session else None,
        }


@dataclass(frozen=True)
class LotteryScope:
    """Separación explícita primary / confirming / follow-up (sin defaults ocultos en UI)."""

    primary_lottery_ids: tuple[str, ...]
    confirming_lottery_ids: tuple[str, ...]
    follow_up_lottery_ids: tuple[str, ...]
    lottery_names: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.primary_lottery_ids:
            raise ValueError("primary_lottery_ids must not be empty")
        if not self.confirming_lottery_ids:
            raise ValueError("confirming_lottery_ids must not be empty")
        if not self.follow_up_lottery_ids:
            raise ValueError("follow_up_lottery_ids must not be empty")

    @staticmethod
    def default_follow_primary(
        primary: list[str] | tuple[str, ...],
        confirming: list[str] | tuple[str, ...] | None = None,
        *,
        names: dict[str, str] | None = None,
    ) -> "LotteryScope":
        prim = tuple(str(x) for x in primary)
        conf = tuple(str(x) for x in (confirming if confirming is not None else prim))
        return LotteryScope(
            primary_lottery_ids=prim,
            confirming_lottery_ids=conf,
            follow_up_lottery_ids=prim,  # default visible: misma principal
            lottery_names=dict(names or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_lottery_ids": list(self.primary_lottery_ids),
            "confirming_lottery_ids": list(self.confirming_lottery_ids),
            "follow_up_lottery_ids": list(self.follow_up_lottery_ids),
            "lottery_names": dict(self.lottery_names),
            "follow_up_default": "same_as_primary",
        }


@dataclass(frozen=True)
class DrawRef:
    draw_id: str
    lottery_id: str
    lottery_name: str
    draw_date: date
    draw_time: time | None = None
    numbers: tuple[tuple[int | str, int], ...] = ()  # (position, number)

    def numbers_1_to_100(self) -> list[int]:
        return [int(n) for _, n in self.numbers if 1 <= int(n) <= 100]

    def local_datetime(self, tz_name: str) -> datetime:
        tz = ZoneInfo(tz_name)
        t = self.draw_time or time(0, 0)
        return datetime(
            self.draw_date.year,
            self.draw_date.month,
            self.draw_date.day,
            t.hour,
            t.minute,
            t.second,
            tzinfo=tz,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "draw_id": self.draw_id,
            "lottery_id": self.lottery_id,
            "lottery_name": self.lottery_name,
            "draw_date": self.draw_date.isoformat(),
            "draw_time": self.draw_time.isoformat() if self.draw_time else None,
            "numbers": [{"position": p, "drawn_number": n} for p, n in self.numbers],
        }


@dataclass
class ConfirmingHit:
    confirmer_number: int
    confirmer_lottery_id: str
    confirmer_lottery_name: str
    confirmer_draw_id: str
    confirmer_datetime: str
    confirmer_position: int | str | None
    relation_mode: str
    points: int = 1
    score_delta: int = 1  # alias explícito: +1 al candidato T1
    candidate_strengthened: int = 0
    dedupe_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PosteriorOutcome:
    candidate: int
    anchor_draw_id: str
    confirmation_draw_ids: list[str]
    follow_up_lottery_ids: list[str]
    first_response_draw_id: str | None
    draws_until_response: int | None
    responded_next_draw: bool | None  # None = censored for horizon 1
    responded_within_2: bool | None
    responded_within_3: bool | None
    responded_within_5: bool | None
    responded_within_10: bool | None
    censored: bool  # True if max horizon not fully evaluable
    censored_horizons: list[str] = field(default_factory=list)
    draws_examined: list[str] = field(default_factory=list)
    max_horizon: int = 10

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AtomicRelationEvent:
    """Nivel A: N → C → V (relación atómica)."""

    event_id: str
    observed_number: int
    mother_code: int
    candidate: int
    confirmer: int
    table1_candidates: list[int]
    candidate_table2_code: int
    candidate_table2_group: list[int]
    anchor: DrawRef
    hit: ConfirmingHit
    posterior: PosteriorOutcome | None = None
    confirmation_window: dict[str, Any] = field(default_factory=dict)
    lottery_scope: dict[str, Any] = field(default_factory=dict)
    methodology_version: str = METHODOLOGY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": "atomic",
            "event_id": self.event_id,
            "observed_number": self.observed_number,
            "mother_code": self.mother_code,
            "candidate": self.candidate,
            "confirmer": self.confirmer,
            "table1_candidates": self.table1_candidates,
            "candidate_table2_code": self.candidate_table2_code,
            "candidate_table2_group": self.candidate_table2_group,
            "anchor": self.anchor.to_dict(),
            "hit": self.hit.to_dict(),
            "posterior": self.posterior.to_dict() if self.posterior else None,
            "confirmation_window": self.confirmation_window,
            "lottery_scope": self.lottery_scope,
            "methodology_version": self.methodology_version,
        }


@dataclass
class CombinationRelationEvent:
    """Nivel B: N → C → frozenset(Vs) normalizado."""

    event_id: str
    observed_number: int
    mother_code: int
    candidate: int
    confirmers: list[int]  # sorted unique
    confirmers_key: str  # "6,9,11"
    atomic_event_ids: list[str]
    hits: list[ConfirmingHit]
    score_raw: int
    anchor: DrawRef
    posterior: PosteriorOutcome | None = None
    confirmation_window: dict[str, Any] = field(default_factory=dict)
    lottery_scope: dict[str, Any] = field(default_factory=dict)
    methodology_version: str = METHODOLOGY_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": "combination",
            "event_id": self.event_id,
            "observed_number": self.observed_number,
            "mother_code": self.mother_code,
            "candidate": self.candidate,
            "confirmers": self.confirmers,
            "confirmers_key": self.confirmers_key,
            "atomic_event_ids": self.atomic_event_ids,
            "hits": [h.to_dict() for h in self.hits],
            "score_raw": self.score_raw,
            "anchor": self.anchor.to_dict(),
            "posterior": self.posterior.to_dict() if self.posterior else None,
            "confirmation_window": self.confirmation_window,
            "lottery_scope": self.lottery_scope,
            "methodology_version": self.methodology_version,
        }


@dataclass
class HorizonRate:
    horizon: str
    numerator: int
    denominator: int  # evaluable (excludes censored for this horizon)
    rate: float | None
    sample_size: int
    censored_count: int
    sample_tier: SampleTier
    sample_warning: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "horizon": self.horizon,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "rate": self.rate,
            "rate_percent": None if self.rate is None else round(100.0 * self.rate, 4),
            "sample_size": self.sample_size,
            "censored_count": self.censored_count,
            "sample_tier": self.sample_tier.value,
            "sample_warning": self.sample_warning,
            "label": "tasa_historica_respuesta_observada",
            "not_probability_of_winning": True,
        }


@dataclass
class CycleStats:
    min: float | None
    max: float | None
    mean: float | None
    median: float | None
    stdev: float | None
    percentiles: dict[str, float]
    distribution: dict[str, int]
    events_with_response: int
    events_without_response_in_window: int
    events_censored: int
    observed_cycles: list[int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
