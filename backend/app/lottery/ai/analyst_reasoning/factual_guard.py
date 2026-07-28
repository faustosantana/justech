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
    r"("
    r"(?<!\bno\s)(?<!\bno\ses\s)seguro\s+que\s+(va\s+a\s+)?sal|"
    r"garantizad[oa]\s+(que\s+)?(sal|ganar|ganar[aá])|"
    r"sin\s+duda\s+saldr[aá]|"
    r"mañana\s+sale\s+el|"
    r"el\s+pr[oó]ximo\s+sorteo\s+(ser[aá]|trae)\s+el|"
    r"\bpredigo\s+que\b|"
    r"\bva\s+a\s+salir\s+el\s+\d{1,2}\b"
    r")",
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
                for m in re.finditer(
                    r"\b(\d{1,5})\s+(ocasiones|veces|coincidencias|apariciones)\b",
                    raw,
                    re.I,
                ):
                    if int(m.group(1)) != t:
                        violations.append(f"count_mismatch:{m.group(1)}!={t}")

        # Subjects: strip ISO dates, clock times, and NY draw labels first
        scrubbed = _ISO_DATE.sub(" ", raw)
        scrubbed = re.sub(r"\b20\d{2}\b", " ", scrubbed)  # years
        scrubbed = re.sub(
            r"\bNew\s+York\s+\d{1,2}\s*[:.]\s*\d{2}\b", " NewYork ", scrubbed, flags=re.I
        )
        scrubbed = re.sub(r"\b\d{1,2}\s*[:.]\s*\d{2}\b", " ", scrubbed)  # times
        scrubbed = re.sub(
            r"\b\d{1,2}\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b",
            " ",
            scrubbed,
            flags=re.I,
        )
        scrubbed = re.sub(r"\b([1-9]|1[0-2])\s+loter", " loter", scrubbed, flags=re.I)
        allowed_nums = {str(int(s)) for s in package.subjects if str(s).isdigit()}
        allowed_nums |= {s.zfill(2) for s in package.subjects if str(s).isdigit()}
        # Allow position-like, months, and scope count
        soft_ok = {str(i) for i in range(0, 32)} | {str(i).zfill(2) for i in range(0, 32)}
        if total is not None:
            try:
                soft_ok.add(str(int(total)))
                soft_ok.add(str(int(total)).zfill(2))
            except (TypeError, ValueError):
                pass
        if allowed_nums:
            claimed: set[str] = set()
            for m in _NUMBER.finditer(scrubbed):
                n = m.group(1)
                claimed.add(n.zfill(2))
                claimed.add(str(int(n)))
            extras = claimed - allowed_nums - {str(int(x)) for x in allowed_nums if str(x).isdigit()}
            hard_extras = extras - soft_ok
            # Alien balls 32–99 claimed as if they were subjects
            alien = {x for x in hard_extras if x.isdigit() and 32 <= int(x) <= 99}
            # Explicit "el NN" / "número NN" outside allowed subjects
            explicit_alien = []
            for m in re.finditer(
                r"\b(?:el|n[uú]mero|numero)\s+(\d{1,2})\b", scrubbed, re.I
            ):
                n = m.group(1).zfill(2)
                if n not in {x.zfill(2) for x in allowed_nums} and int(n) >= 13:
                    explicit_alien.append(n)
            if len(set(explicit_alien)) >= 2 or len(alien) >= 3:
                violations.append(
                    f"extra_subjects:{sorted(set(explicit_alien) | alien)[:6]}"
                )

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
