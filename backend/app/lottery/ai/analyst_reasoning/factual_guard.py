"""Factual Guard — reject Huawei outputs that invent or alter verified facts."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from app.lottery.ai.analyst_reasoning.allowed_subjects import AllowedSubjectSet
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

# Contexts where a 1–2 digit number is NOT a subject ball
_NON_SUBJECT_CONTEXT = re.compile(
    r"("
    r"\d{1,2}\s*(?::|h)\s*\d{2}"  # times
    r"|\b20\d{2}-\d{2}-\d{2}\b"
    r"|\b20\d{2}\b"  # years
    r"|\b(?:tabla|table|top|últim[oa]s?|ultim[oa]s?|primer[oa]s?|próxim[oa]s?|proxim[oa]s?)\s+\d{1,2}\b"
    r"|\b\d{1,2}\s*(?:ª|º|°)?\s*posici[oó]n"
    r"|\bposici[oó]n(?:es)?\s+\d{1,2}\b"
    r"|\b\d{1,2}\s*(?:ª|º|°)\b"
    r"|\b\d{1,5}\s+(?:ocasiones|veces|coincidencias|apariciones|fechas|registros|d[ií]as|sorteos|loter[ií]as)\b"
    r"|\b(?:total|coincid(?:ieron|en|e)|conteo|cantidad)\s+(?:de\s+)?(?:en\s+)?\d{1,5}\b"
    r"|\blas?\s+otras?\s+\d{1,2}\b"
    r"|\b\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b"
    r")",
    re.I,
)

_SUBJECT_EXPLICIT = re.compile(
    r"\b(?:"
    r"(?:el|los|la|las|n[uú]mero|numero|bola|cifra)\s+(\d{1,2})"
    r"|(\d{1,2})\s+y\s+(\d{1,2})"
    r"|(?<![$\d])(\d{1,2})(?=\s+y\s+(?:el\s+)?\d{1,2})"
    r")\b",
    re.I,
)


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

        if _EXTERNAL.search(raw):
            violations.append("external_lottery")

        if _GUARANTEED.search(raw):
            violations.append("guaranteed_prediction")

        # --- date_guard ---
        allowed_dates = set(package.dates)
        for d in _ISO_DATE.findall(raw):
            if allowed_dates and d not in allowed_dates:
                violations.append(f"unknown_date:{d}")
            elif not allowed_dates:
                violations.append(f"invented_date:{d}")

        # --- count_guard ---
        total = package.counts.get("total")
        if total is not None:
            try:
                t = int(total)
            except (TypeError, ValueError):
                t = None
            if t is not None:
                count_pat = re.compile(
                    r"\b(\d{1,5})\s+("
                    r"ocasiones|veces|coincidencias|apariciones|"
                    r"fechas(\s+[a-záéíóú]+)?|registros(\s+de\s+ocurrencias)?|"
                    r"d[ií]as(\s+[a-záéíóú]+)?|sorteos"
                    r")\b",
                    re.I,
                )
                for m in count_pat.finditer(raw):
                    claimed = int(m.group(1))
                    if claimed in {7, 1, 2, 3}:
                        continue
                    if claimed != t:
                        # Allow explicit sample-size wording (not a coincidence total)
                        span = raw[max(0, m.start() - 32) : m.end() + 24]
                        if re.search(
                            r"(?:\bla\s+muestra\s+de|\bmuestra\s+truncad|\bsample(?:\s+size)?(?:\s+of)?)\s*\d{1,5}\b",
                            span,
                            re.I,
                        ):
                            continue
                        # Also: "muestra de 40 fechas es truncada"
                        if re.search(r"\bmuestra\s+de\s+\d{1,5}\s+fechas\b", span, re.I) and re.search(
                            r"truncad|sample", span, re.I
                        ):
                            continue
                        violations.append(f"count_mismatch:{claimed}!={t}")
                # Invented partials: "en 10 de esas ocasiones/días"
                for m in re.finditer(
                    r"\b(?:en\s+)?(\d{1,5})\s+de\s+(?:esas|esos|ellos|ellas)\b",
                    raw,
                    re.I,
                ):
                    claimed = int(m.group(1))
                    if claimed not in {7, 1, 2, 3, t}:
                        violations.append(f"count_mismatch:{claimed}!={t}")
                for m in re.finditer(
                    r"\b(?:total|coincid(?:ieron|en|e))\s+(?:en\s+)?(\d{1,5})\b",
                    raw,
                    re.I,
                ):
                    claimed = int(m.group(1))
                    if claimed not in {7, 1, 2, 3, t}:
                        violations.append(f"count_mismatch:{claimed}!={t}")
                # Sample-size confusion: model reports len(dates) as if it were the total
                sample_n = min(40, len(package.dates or []))
                if sample_n and sample_n != t:
                    for m in re.finditer(
                        rf"\b{sample_n}\s+(?:fechas|ocasiones|coincidencias|apariciones|registros|d[ií]as)\b",
                        raw,
                        re.I,
                    ):
                        span = raw[max(0, m.start() - 24) : m.end() + 24]
                        if re.search(r"\bmuestra\b|\bsample\b|\btruncad", span, re.I):
                            continue
                        violations.append(f"count_mismatch:{sample_n}!={t}")
                        break

        # --- subject_guard (linguistic, not global digit scrape) ---
        violations.extend(cls._subject_guard(raw, package))

        # --- lottery_guard ---
        for m in re.finditer(
            r"\b(Quiniela\s+\w+|Loteria\s+\w+|Gana\s+M[aá]s|New\s+York\s+[\d:]+)\b",
            raw,
            re.I,
        ):
            name = m.group(1)
            if not is_official_lottery(name) and not cls._partial_official(name):
                violations.append(f"non_official_lottery:{name}")

        if violations:
            result = GuardResult(False, raw, violations[0], violations)
        else:
            result = GuardResult(True, raw, None, [])
        try:
            from app.lottery.ai.forensics import ForensicTraceService, get_correlation_id

            tr = ForensicTraceService(get_correlation_id())
            if tr.enabled:
                tr.record_transform(
                    "factual_guard.output",
                    component="FactualGuard",
                    file="factual_guard.py",
                    function="validate",
                    input=raw,
                    output=result.text if result.passed else f"[REJECTED:{result.rejection_reason}]",
                )
                tr.event(
                    "factual_guard.output",
                    component="FactualGuard",
                    file="factual_guard.py",
                    function="validate",
                    extra={
                        "passed": result.passed,
                        "rejection_reason": result.rejection_reason,
                        "violations": list(result.violations or [])[:20],
                    },
                )
        except Exception:  # noqa: BLE001
            pass
        return result

    @classmethod
    def _subject_guard(cls, raw: str, package: EvidencePackage) -> list[str]:
        allowed = AllowedSubjectSet.from_evidence_package(package)
        if not allowed.canonical:
            return []

        # Mask non-subject numeric contexts before extracting candidate subjects
        scrubbed = _NON_SUBJECT_CONTEXT.sub(" ", raw)
        scrubbed = _ISO_DATE.sub(" ", scrubbed)
        scrubbed = re.sub(r"\bNew\s+York\s+\d{1,2}\s*[:.]\s*\d{2}\b", " NewYork ", scrubbed, flags=re.I)
        # Ordinals / position labels: 1ro, 2do, 3ro, 4to, 5º…
        scrubbed = re.sub(
            r"\b\d{1,2}\s*(?:ro|do|to|mo|vo|no|º|°|ª)\b",
            " ",
            scrubbed,
            flags=re.I,
        )
        scrubbed = re.sub(r"\b(?:1ro|2do|3ro|4to|5to|6to|7mo|8vo|9no|10mo)\b", " ", scrubbed, flags=re.I)
        # Day-month fragments like 23/07 or 08-07-2026
        scrubbed = re.sub(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", " ", scrubbed)

        claimed: set[str] = set()
        # Explicit subject mentions
        for m in re.finditer(
            r"\b(?:el|los|la|las|n[uú]mero|numero|bola)\s+(\d{1,2})\b",
            scrubbed,
            re.I,
        ):
            claimed.add(str(int(m.group(1))))
        # Pair patterns "50 y 90"
        for m in re.finditer(r"\b(\d{1,2})\s+y\s+(?:el\s+)?(\d{1,2})\b", scrubbed, re.I):
            claimed.add(str(int(m.group(1))))
            claimed.add(str(int(m.group(2))))
        # Bold/markdown emphasis often used for subjects: **50**
        for m in re.finditer(r"\*\*(\d{1,2})\*\*", scrubbed):
            claimed.add(str(int(m.group(1))))

        extras = sorted(n for n in claimed if not allowed.contains(n))
        if extras:
            return [f"extra_subjects:{extras[:8]}"]

        # Also catch invented related balls presented as lists of "números" / "vecinos" / "compañeros"
        invent_pat = re.compile(
            r"(?:vecinos?|compa[nñ]eros?|relacionad[oa]s?|candidatos?|n[uú]meros?\s+fuertes?)"
            r"[^.\n]{0,80}?(\d{1,2}(?:\s*,\s*\d{1,2}){1,6})",
            re.I,
        )
        for m in invent_pat.finditer(raw):
            nums = [str(int(x)) for x in re.findall(r"\d{1,2}", m.group(1))]
            bad = [n for n in nums if not allowed.contains(n)]
            if bad:
                return [f"extra_subjects:{bad[:8]}"]
        return []

    @staticmethod
    def _partial_official(name: str) -> bool:
        n = unicodedata.normalize("NFKD", name.lower())
        n = "".join(c for c in n if not unicodedata.combining(c))
        keys = ("nacional", "leidsa", "loteka", "real", "gana mas", "new york")
        return any(k in n for k in keys)
