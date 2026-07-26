"""Blind train/val/test dataset from historical activations (manual cases excluded)."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any


# Benchmark-only fingerprints — excluded from blind splits.
MANUAL_BENCHMARK_FINGERPRINTS: set[frozenset[int]] = {
    frozenset({41, 70}),
    frozenset({41, 62}),
    frozenset({49, 44, 70}),
    frozenset({35, 14}),
    frozenset({39, 58}),
}

MANUAL_BENCHMARK_CASES = [
    {"id": "M1", "numbers": [41, 41, 70], "expected": 29},
    {"id": "M2", "numbers": [41, 62], "expected": 75},
    {"id": "M3", "numbers": [49, 44, 70], "expected": 35},
    {"id": "M4", "numbers": [35, 14], "expected": 54},
    {"id": "M5", "numbers": [39, 58], "expected": 94},
]


@dataclass
class BlindScenario:
    scenario_id: str
    split: str
    case_date: str
    year: int
    observed_numbers: list[int]
    historical_fuerte: int
    origin: int
    confirmer: int
    origin_lottery: str
    confirmer_lottery: str
    origin_position: int
    confirmer_position: int
    n_confirmers: int
    n_fuertes_same_day: int
    fuerte_appeared: bool
    first_day_offset: int | None
    first_lottery: str | None
    first_draw_position: int | None
    activation_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[6]


def default_activations_path() -> Path:
    return _repo_root() / "artifacts" / "deep_mathematical_audit" / "all_activations.csv"


def is_manual_benchmark(observed: list[int]) -> bool:
    return frozenset(int(x) for x in observed) in MANUAL_BENCHMARK_FINGERPRINTS


def load_activation_rows(path: Path | None = None) -> list[dict[str, str]]:
    p = path or default_activations_path()
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_blind_dataset(
    *,
    activations_path: Path | None = None,
    train_ratio: float = 0.60,
    val_ratio: float = 0.20,
    seed: int = 20260726,
) -> dict[str, Any]:
    """
    Time-ordered split of historical official activations.

    Observed inputs = {origin, confirmer} (+ other confirmers not available as list
    in CSV — use origin+confirmer). Manual partner cases are excluded from all splits
    and reserved as final benchmark only.
    """
    rows = load_activation_rows(activations_path)
    scenarios: list[BlindScenario] = []
    excluded_manual = 0

    for row in rows:
        origin = int(row["origin"])
        confirmer = int(row["confirmer"])
        fuerte = int(row["fuerte"])
        observed = sorted({origin, confirmer})
        if is_manual_benchmark(observed):
            excluded_manual += 1
            continue
        # Skip degenerate
        if origin == confirmer:
            continue
        offset = row.get("first_day_offset") or ""
        try:
            day_off = int(float(offset)) if str(offset).strip() else None
        except ValueError:
            day_off = None
        appeared = str(row.get("fuerte_appeared", "")).lower() in {"true", "1", "yes"}
        case_date = str(row["case_date"])[:10]
        year = int(row.get("year") or case_date[:4])
        sid = hashlib.sha1(
            f"{row.get('activation_id')}|{origin}|{confirmer}|{fuerte}".encode()
        ).hexdigest()[:16]
        scenarios.append(
            BlindScenario(
                scenario_id=sid,
                split="",  # filled after sort
                case_date=case_date,
                year=year,
                observed_numbers=observed,
                historical_fuerte=fuerte,
                origin=origin,
                confirmer=confirmer,
                origin_lottery=str(row.get("origin_lottery") or ""),
                confirmer_lottery=str(row.get("confirmer_lottery") or ""),
                origin_position=int(row.get("origin_draw_position") or 1),
                confirmer_position=int(row.get("confirmer_draw_position") or 1),
                n_confirmers=int(row.get("n_confirmers") or 1),
                n_fuertes_same_day=int(row.get("n_fuertes_same_day") or 1),
                fuerte_appeared=appeared,
                first_day_offset=day_off,
                first_lottery=row.get("first_lottery") or None,
                first_draw_position=int(row["first_draw_position"])
                if str(row.get("first_draw_position") or "").strip().isdigit()
                else None,
                activation_id=str(row.get("activation_id") or sid),
            )
        )

    scenarios.sort(key=lambda s: (s.case_date, s.scenario_id))
    n = len(scenarios)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    for i, s in enumerate(scenarios):
        if i < n_train:
            s.split = "train"
        elif i < n_train + n_val:
            s.split = "validation"
        else:
            s.split = "test"

    by_split = {"train": [], "validation": [], "test": []}
    for s in scenarios:
        by_split[s.split].append(s.to_dict())

    return {
        "seed": seed,
        "source": str(activations_path or default_activations_path()),
        "methodology_note": (
            "Blind set built from historical official T1×T2 activations. "
            "Manual partner cases excluded from train/val/test; reserved as benchmark."
        ),
        "excluded_manual_rows": excluded_manual,
        "total_scenarios": n,
        "counts": {k: len(v) for k, v in by_split.items()},
        "date_range": {
            "min": scenarios[0].case_date if scenarios else None,
            "max": scenarios[-1].case_date if scenarios else None,
        },
        "splits": by_split,
        "manual_benchmark_reserved": MANUAL_BENCHMARK_CASES,
    }
