"""Factual Guard — reject Huawei outputs that invent or alter verified facts."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from app.lottery.ai.analyst_reasoning.evidence_package import EvidencePackage
from app.lottery.ai.official_lottery_scope import is_official_lottery


_EXTERNAL = re.compile(
    r"\b("
    r"haiti\s*bolet|king\s*lottery|anguila|cash\s*4\s*life|cash4life|"
    r"florida\s*(dia|noche)?|el\s+agarra|la\s+suerte\s+\d"
    r")\b",
    re.I,
)
_GUARANTEED = re.compile(
    r"\b("
    r"seguro\s+que\s+(va\s+a\s+)?sal|"
    r"garantizad[oa]|sin\s+duda\s+saldr[aá]|"
    r"mañana\s+sale|el\s+pr[oó]ximo\s+sorteo\s+(ser[aá]|trae)|"
    r"predigo\s+que|va\s+a\s+salir\s+el\s+\d{1,2}"
    r")\b",
    re.I,
)
_ISO_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_NUMBER = re.compile(r"(?<!\d)(\d{1,2})(?!\d)")


@dataclass
class GuardResult:
    passed: bool
    text: str
    rejection_reason: str | None = None
    violations: list[str] = field(default_factory=list)


class FactualGuard:
    @classmethod
    def validate(cls, text: str, package: EvidencePackage) -> GuardResult:
        raw = (text or "").strip()
        if len(raw) < 20:
            return GuardResult(False, raw, "too_short", ["too_short"])

        violations: list[str] = []

        # External lotteries
        if _EXTERNAL.search(raw):
            violations.append("external_lottery")

        # Guaranteed prediction language
        if _GUARANTEED.search(raw):
            violations.append("guaranteed_prediction")

        # Dates must be in evidence (if any date claimed)
        allowed_dates = set(package.dates)
        for d in _ISO_DATE.findall(raw):
            if allowed_dates and d not in allowed_dates:
                violations.append(f"unknown_date:{d}")
            elif not allowed_dates:
                # No dates in package → claiming ISO dates is invention
                violations.append(f"invented_date:{d}")

        # Counts: if total known, model must not state a different total nearby
        total = package.counts.get("total")
        if total is not None:
            try:
                t = int(total)
            except (TypeError, ValueError):
                t = None
            if t is not None:
                # Flag "N ocasiones/veces/coincidencias" where N != total
                for m in re.finditer(
                    r"\b(\d{1,5})\s+(ocasiones|veces|coincidencias|apariciones)\b",
                    raw,
                    re.I,
                ):
                    if int(m.group(1)) != t:
                        violations.append(f"count_mismatch:{m.group(1)}!={t}")

        # Subjects: if package has subjects, don't introduce many new ball numbers
        allowed_nums = {str(int(s)) for s in package.subjects if str(s).isdigit()}
        allowed_nums |= {s.zfill(2) for s in package.subjects if str(s).isdigit()}
        if allowed_nums:
            claimed = set()
            for m in _NUMBER.finditer(raw):
                n = m.group(1)
                # skip years already caught; skip totals
                if len(n) == 4:
                    continue
                claimed.add(n.zfill(2))
                claimed.add(str(int(n)))
            # Allow official scope count "7"
            claimed.discard("07")
            claimed.discard("7")
            if total is not None:
                claimed.discard(str(int(total)))
                claimed.discard(str(int(total)).zfill(2))
            extras = claimed - allowed_nums - {str(int(x)) for x in allowed_nums if x.isdigit()}
            # Soft: only fail if many extras (avoid false positives on positions 1,2,3)
            soft_ok = {"01", "1", "02", "2", "03", "3", "04", "4"}
            hard_extras = extras - soft_ok
            if len(hard_extras) >= 3:
                violations.append(f"extra_subjects:{sorted(hard_extras)[:6]}")

        # Lottery names: if a known official DB name pattern appears that's not official → already external
        # Soft check: "Quiniela X" / "Loteria X" must be official if present
        for m in re.finditer(
            r"\b(Quiniela\s+\w+|Loteria\s+\w+|Gana\s+M[aá]s|New\s+York\s+[\d:]+)\b",
            raw,
            re.I,
        ):
            name = m.group(1)
            if not is_official_lottery(name) and not cls._partial_official(name):
                violations.append(f"non_official_lottery:{name}")

        if violations:
            return GuardResult(False, raw, violations[0], violations)
        return GuardResult(True, raw, None, [])

    @staticmethod
    def _partial_official(name: str) -> bool:
        n = unicodedata.normalize("NFKD", name.lower())
        n = "".join(c for c in n if not unicodedata.combining(c))
        keys = ("nacional", "leidsa", "loteka", "real", "gana mas", "new york")
        return any(k in n for k in keys)
