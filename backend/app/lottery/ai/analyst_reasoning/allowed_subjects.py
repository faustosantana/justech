"""Canonical allowed subjects derived from Evidence Package (and optional contract)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage

_BALL = re.compile(r"^\d{1,2}$")


def normalize_ball(value: Any) -> str | None:
    """Normalize lottery ball subjects: 7 / '7' / '07' → canonical forms."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or not _BALL.match(s):
        return None
    try:
        n = int(s)
    except ValueError:
        return None
    if n < 0 or n > 99:
        return None
    return str(n)


@dataclass(frozen=True)
class AllowedSubjectSet:
    """Subjects the model may mention as analysis objects."""

    canonical: frozenset[str] = field(default_factory=frozenset)
    padded: frozenset[str] = field(default_factory=frozenset)
    allow_related: bool = False
    related: frozenset[str] = field(default_factory=frozenset)

    def contains(self, value: Any) -> bool:
        n = normalize_ball(value)
        if n is None:
            return False
        if n in self.canonical or n.zfill(2) in self.padded:
            return True
        if self.allow_related and (n in self.related or n.zfill(2) in self.related):
            return True
        return False

    def as_forms(self) -> set[str]:
        out: set[str] = set(self.canonical) | set(self.padded)
        if self.allow_related:
            out |= {str(int(x)) for x in self.related if str(x).isdigit()}
            out |= {str(int(x)).zfill(2) for x in self.related if str(x).isdigit()}
        return out

    def to_contract_list(self) -> list[str]:
        return sorted(self.canonical, key=lambda x: int(x))

    @classmethod
    def from_values(cls, values: Iterable[Any], *, allow_related: bool = False, related: Iterable[Any] = ()) -> AllowedSubjectSet:
        cans: set[str] = set()
        pads: set[str] = set()
        for v in values:
            n = normalize_ball(v)
            if n is None:
                continue
            cans.add(n)
            pads.add(n.zfill(2))
        rel: set[str] = set()
        for v in related:
            n = normalize_ball(v)
            if n is None:
                continue
            rel.add(n)
            rel.add(n.zfill(2))
        return cls(
            canonical=frozenset(cans),
            padded=frozenset(pads),
            allow_related=bool(allow_related),
            related=frozenset(rel),
        )

    @classmethod
    def from_evidence_package(cls, package: EvidencePackage) -> AllowedSubjectSet:
        """Build allowed subjects from package fields + optional response_contract."""
        values: list[Any] = list(package.subjects or [])
        allow_related = False
        related: list[Any] = []

        # Occurrences / source rows may carry the same subjects
        for row in list(package.occurrences or [])[:50] + list(package.source_rows or [])[:50]:
            if not isinstance(row, dict):
                continue
            for key in ("number", "num", "ball", "subject", "n1", "n2"):
                if key in row:
                    values.append(row.get(key))
            pair = row.get("numbers") or row.get("subjects")
            if isinstance(pair, (list, tuple)):
                values.extend(pair)

        comp = package.comparison_data if isinstance(package.comparison_data, dict) else {}
        for key in ("subjects", "numbers", "left", "right", "a", "b"):
            v = comp.get(key)
            if isinstance(v, (list, tuple)):
                values.extend(v)
            elif v is not None and key in {"left", "right", "a", "b"}:
                values.append(v)

        # Optional backward-compatible contract (ignored by legacy if unused)
        contract = None
        extra = getattr(package, "response_contract", None)
        if isinstance(extra, dict):
            contract = extra
        elif isinstance(package.counts, dict) and isinstance(package.counts.get("_response_contract"), dict):
            # never preferred — counts must stay clean
            contract = None
        # Prefer model_extra / dump field if present on package as arbitrary attribute
        dump = package.model_dump() if hasattr(package, "model_dump") else {}
        if isinstance(dump.get("response_contract"), dict):
            contract = dump["response_contract"]

        if isinstance(contract, dict):
            if contract.get("allowed_subjects"):
                values = list(contract.get("allowed_subjects") or [])
            allow_related = bool(contract.get("allow_related_subjects"))
            related = list(contract.get("related_subjects") or [])

        return cls.from_values(values, allow_related=allow_related, related=related)
