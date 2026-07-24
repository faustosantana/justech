"""Modelos de dominio del Motor de Relaciones Numéricas (sin ORM)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, time
from enum import Enum
from typing import Any, Literal
from uuid import UUID


class TableKind(str, Enum):
    TABLE_1 = "table_1"
    TABLE_2 = "table_2"


@dataclass(frozen=True)
class FormattedComputation:
    number: int
    table: TableKind
    formula: str
    visible_value: str
    digits_without_point: str
    digit_count: int
    digit_list: tuple[int, ...]
    code: int

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["table"] = self.table.value
        d["digit_list"] = list(self.digit_list)
        return d


@dataclass(frozen=True)
class OccurrenceLimit:
    mode: Literal["last_k", "all"]
    k: int | None = None

    def __post_init__(self) -> None:
        if self.mode == "last_k":
            if self.k is None or int(self.k) < 1:
                raise ValueError("last_k requires k >= 1")
        elif self.mode == "all":
            pass
        else:
            raise ValueError(f"unknown occurrence limit mode: {self.mode}")

    @staticmethod
    def last_k(k: int) -> "OccurrenceLimit":
        return OccurrenceLimit(mode="last_k", k=int(k))

    @staticmethod
    def all() -> "OccurrenceLimit":
        return OccurrenceLimit(mode="all", k=None)

    def to_dict(self) -> dict[str, Any]:
        if self.mode == "all":
            return {"mode": "all"}
        return {"mode": "last_k", "k": self.k}


@dataclass(frozen=True)
class DrawNumberRef:
    position: int | str
    drawn_number: int
    position_label: str | None = None


@dataclass(frozen=True)
class HistoricalOccurrence:
    lottery_id: UUID | str
    lottery_name: str
    draw_id: UUID | str
    draw_date: date
    observed_number: int
    draw_numbers: tuple[DrawNumberRef, ...]
    draw_time: time | None = None

    def numbers_1_to_100(self) -> list[int]:
        from app.lottery.numeric_relations.constants import N_MAX, N_MIN

        out: list[int] = []
        for ref in self.draw_numbers:
            n = int(ref.drawn_number)
            if N_MIN <= n <= N_MAX:
                out.append(n)
        return out


@dataclass
class Match:
    companion: int
    neighbor: int
    lottery_id: UUID | str
    lottery_name: str
    draw_id: UUID | str
    draw_date: date
    position: int | str
    position_label: str | None
    observed_number: int
    mother_code: int
    table2_code: int
    table2_group: list[int]
    neighbors: list[int]
    points: int = 1
    dedupe_key: str = ""
    trace: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "companion": self.companion,
            "neighbor": self.neighbor,
            "lottery_id": str(self.lottery_id),
            "lottery_name": self.lottery_name,
            "draw_id": str(self.draw_id),
            "draw_date": self.draw_date.isoformat(),
            "position": self.position,
            "position_label": self.position_label,
            "observed_number": self.observed_number,
            "mother_code": self.mother_code,
            "table2_code": self.table2_code,
            "table2_group": list(self.table2_group),
            "neighbors": list(self.neighbors),
            "points": self.points,
            "dedupe_key": self.dedupe_key,
            "trace": self.trace,
        }


@dataclass
class StrengthenedCandidate:
    number: int
    table1_code: int
    table2_code: int
    table2_group: list[int]
    neighbors: list[int]
    matched_neighbors: list[int]
    score: int
    matches: list[Match] = field(default_factory=list)
    trace: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "table1_code": self.table1_code,
            "table2_code": self.table2_code,
            "table2_group": list(self.table2_group),
            "neighbors": list(self.neighbors),
            "matched_neighbors": list(self.matched_neighbors),
            "score": self.score,
            "matches": [m.to_dict() for m in self.matches],
            "trace": self.trace,
        }


@dataclass
class AnalysisResult:
    observed_number: int
    mother_code: int
    primary_table: str
    lottery_ids: list[str]
    lottery_names: list[str]
    occurrence_limit: dict[str, Any]
    occurrences_found: int
    occurrences_used: int
    historical_occurrences: list[dict[str, Any]]
    direct_companions: list[int]
    candidates: list[StrengthenedCandidate]
    analysis_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_number": self.observed_number,
            "mother_code": self.mother_code,
            "primary_table": self.primary_table,
            "lottery_ids": list(self.lottery_ids),
            "lottery_names": list(self.lottery_names),
            "occurrence_limit": dict(self.occurrence_limit),
            "occurrences_found": self.occurrences_found,
            "occurrences_used": self.occurrences_used,
            "historical_occurrences": list(self.historical_occurrences),
            "direct_companions": list(self.direct_companions),
            "companions_analyzed": list(self.direct_companions),
            "ranking": [c.to_dict() for c in self.candidates],
            "candidates": [c.to_dict() for c in self.candidates],
            "analysis_metadata": dict(self.analysis_metadata),
        }
