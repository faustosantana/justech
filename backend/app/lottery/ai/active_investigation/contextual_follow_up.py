"""ContextualFollowUpResolver — map natural follow-ups onto the active investigation."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

RequestedAttribute = Literal[
    "lotteries",
    "positions",
    "date",
    "count",
    "previous_list",
    "after",
    "explain",
    "details",
    "order",
    "filter_lottery",
    "filter_position",
    "compare_prior",
    "other_number",
    # Numeric-relations / table follow-ups (active investigation subject)
    "tabla1",
    "tabla2",
    "companions",
    "neighbors",
    "table_code",
    "history",
    "strongest",
    "compare_neighbors",
    "compare_companions",
    "unknown",
]


def _norm(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


_ATTR_PATTERNS: list[tuple[RequestedAttribute, re.Pattern[str]]] = [
    # Tables / relations first — beat generic "detalles"
    ("compare_companions", re.compile(
        r"\bcompara(r)?\s+(sus\s+|los\s+)?compa[nñ]eros\b|"
        r"\bcompa[nñ]eros?\s+entre\s+(ellos|ambos)\b",
        re.I,
    )),
    ("compare_neighbors", re.compile(
        r"\bcompara(r)?\s+(sus\s+|los\s+)?vecinos\b|"
        r"\bvecinos?\s+entre\s+(ellos|ambos)\b",
        re.I,
    )),
    ("tabla1", re.compile(
        r"\b(y\s+)?(su\s+)?relaci[oó]n\s+(en\s+)?(la\s+)?tabla\s*1\b|"
        r"\b(muestra(me)?|ver|dame)\s+(la\s+)?tabla\s*1\b|"
        r"\ben\s+la\s+tabla\s*1\b|\btabla\s*1\b",
        re.I,
    )),
    ("tabla2", re.compile(
        r"\b(y\s+)?(su\s+)?relaci[oó]n\s+(en\s+)?(la\s+)?tabla\s*2\b|"
        r"\b(muestra(me)?|ver|dame)\s+(la\s+)?tabla\s*2\b|"
        r"\ben\s+la\s+tabla\s*2\b|\btabla\s*2\b",
        re.I,
    )),
    ("companions", re.compile(
        r"\b(cu[aá]les?\s+son\s+)?(sus\s+|los\s+)?compa[nñ]eros\b|"
        r"\bcu[aá]ntos?\s+compa[nñ]eros\b|"
        r"\bcompa[nñ]eros?\s+(de\s+)?(tabla\s*1|codigo|c[oó]digo)\b|"
        r"\b(muestra(me)?|dame)\s+(los\s+)?compa[nñ]eros\b|"
        r"\bqui[eé]n(es)?\s+comparte(n)?\s+el\s+mismo\s+c[oó]digo\b",
        re.I,
    )),
    ("neighbors", re.compile(
        r"\b(cu[aá]les?\s+son\s+)?(sus\s+|los\s+)?vecinos\b|"
        r"\bcu[aá]l\s+vecino\b|\bvecino\s+(sali[oó]|nunca)\b|"
        r"\b(muestra(me)?|dame)\s+(los\s+)?vecinos\b|"
        r"\bvecinos?\s+(de\s+)?(tabla\s*2)?\b",
        re.I,
    )),
    ("table_code", re.compile(
        r"\b(cu[aá]l\s+es\s+)?(su\s+)?c[oó]digo\b|"
        r"\bc[oó]digo\s+(madre|tabla|t1|t2)\b",
        re.I,
    )),
    ("history", re.compile(
        r"\b(muestra(me)?|dame|ver)\s+(el\s+)?hist[oó]rico\b|"
        r"\b[uú]ltimas?\s+salidas\b|\bsus\s+[uú]ltimas?\s+salidas\b|"
        r"\bcu[aá]les?\s+fueron\s+sus\s+[uú]ltimas?\b",
        re.I,
    )),
    ("strongest", re.compile(
        r"\b(cu[aá]l\s+es\s+)?(el\s+)?m[aá]s\s+fuerte\b|"
        r"\bm[aá]s\s+probabilidad\b|\bmejor\s+hist[oó]rico\b|"
        r"\bm[aá]s\s+coincidencias\b|\bcon\s+qui[eé]n\s+coincidi[oó]\s+m[aá]s\b",
        re.I,
    )),
    ("lotteries", re.compile(
        r"\b(en\s+)?(cu[aá]les?|qu[eé])\s+loter[ií]as?\b|"
        r"\bd[oó]nde\s+ocurri[oó]\b|\bd[oó]nde\s+sali[oó]\b|"
        r"\ben\s+qu[eé]\s+loter|"
        r"\b(muestra(me)?|solo)\s+(solamente\s+)?(loteka|nacional|leidsa|real|gana)",
        re.I,
    )),
    ("positions", re.compile(
        r"\b(en\s+)?(qu[eé]|cu[aá]les?)\s+posiciones?\b|"
        r"\by\s+las?\s+posiciones?\b|"
        r"\ben\s+qu[eé]\s+orden\b|"
        r"\blos?\s+dos\s+salieron\s+en\s+primera\b",
        re.I,
    )),
    ("date", re.compile(
        r"\bcu[aá]ndo\s+fue(\s+eso)?\b|\besa\s+fecha\b|\bqu[eé]\s+fecha\b",
        re.I,
    )),
    ("count", re.compile(
        r"\bcu[aá]ntas?\s+veces\b|\bcu[aá]ntas?\s+coinciden|"
        r"\bcu[aá]ntas?\s+coincidencias\b",
        re.I,
    )),
    ("previous_list", re.compile(
        r"\b(coincidencias?\s+)?anteriores?\b|"
        r"\besas?\s+([uú]ltimas?\s+)?(\d{1,2}\s+)?(veces|fechas|coinciden)|"
        r"\bcu[aá]les\s+fueron\b|"
        r"\blas?\s+3\s+coinciden|"
        r"\beste\s+a[nñ]o\b|\bel\s+anterior\b|\ba[nñ]o\s+pasado\b",
        re.I,
    )),
    ("after", re.compile(
        r"\by\s+despu[eé]s\b|\bqu[eé]\s+pas[oó]\s+(luego|despu[eé]s)\b|"
        r"\bposteriores?\b|\bsiete\s+sorteos\s+siguientes\b",
        re.I,
    )),
    ("explain", re.compile(
        r"\bpor\s+qu[eé]\s+dices\b|\bexpl[ií]came\b|\bqu[eé]\s+significa\b|"
        r"\bexpl[ií]came\s+mejor\b|\bpor\s+qu[eé]\b",
        re.I,
    )),
    ("details", re.compile(
        r"\bm[aá]s\s+detalles\b|\bdame\s+m[aá]s\s+detalle|\bamplicame\b|"
        r"\b(muestra(me)?|dame)\s+la\s+relaci[oó]n\b",
        re.I,
    )),
    ("order", re.compile(
        r"\ben\s+qu[eé]\s+orden\s+salieron\b|\bcu[aá]l\s+sali[oó]\s+primero\b",
        re.I,
    )),
    ("compare_prior", re.compile(
        r"\bcompa?ra(lo)?\s+con\s+la\s+coinciden\s+anterior\b",
        re.I,
    )),
    ("other_number", re.compile(
        r"\by\s+el\s+otro\s+n[uú]mero\b|\bel\s+otro\b",
        re.I,
    )),
]


class ContextualFollowUpResolver:
    """Resolve pronouns/demonstratives against the active investigation event."""

    @classmethod
    def detect_attribute(cls, text: str) -> RequestedAttribute | None:
        raw = text or ""
        t = _norm(raw)
        # Named lottery filter («¿Y en Nacional?»)
        from app.services.lottery_intent import _extract_lotteries

        if _extract_lotteries(raw) and len(re.findall(r"\b\d{1,2}\b", raw)) == 0:
            if re.search(r"^\s*(y\s+)?(ahora\s+)?(solo\s+)?en\s+", raw, re.I) or re.search(
                r"\ben\s+(nacional|leidsa|loteka|real|gana)", t
            ):
                return "filter_lottery"
        if re.search(r"\b(solo\s+)?en\s+(primera|segunda|tercera|1ra|2da|3ra)\b", t):
            return "filter_position"
        for attr, pat in _ATTR_PATTERNS:
            if pat.search(raw) or pat.search(t):
                return attr
        return None

    @classmethod
    def is_table_attribute(cls, attr: str | None) -> bool:
        return attr in {
            "tabla1",
            "tabla2",
            "companions",
            "neighbors",
            "table_code",
            "compare_neighbors",
            "compare_companions",
            "strongest",
        }

    @classmethod
    def is_short_contextual_follow_up(cls, text: str) -> bool:
        attr = cls.detect_attribute(text)
        if attr:
            return True
        t = _norm(text).strip(" ¿?¡!.")
        return bool(
            re.match(
                r"^(y\s+)?(eso|esa|ese|ambos|los\s+dos|esa\s+coinciden|"
                r"ese\s+resultado|la\s+anterior|esa\s+fecha|"
                r"la\s+tabla|tabla\s*[12]|los\s+compa[nñ]eros|los\s+vecinos)$",
                t,
            )
        )

    @classmethod
    def resolve(
        cls,
        text: str,
        *,
        investigation: Any | None,
        state: Any | None = None,
    ) -> dict[str, Any] | None:
        if investigation is None or getattr(investigation, "status", None) == "expired":
            return None
        subjects = list(getattr(investigation, "subjects", None) or [])
        if len(subjects) < 1 and state is not None:
            subjects = list(getattr(state, "active_pair", None) or getattr(state, "active_numbers", None) or [])
        attr = cls.detect_attribute(text)
        if not attr and not cls.is_short_contextual_follow_up(text):
            return None
        relation = getattr(investigation, "relation", None) or getattr(investigation, "metric", None)
        return {
            "requested_attribute": attr or "details",
            "inherited_subjects": subjects[:8],
            "inherited_relation": relation,
            "inherited_metric": getattr(investigation, "metric", None) or relation,
            "refers_to": "active_investigation.last_event",
            "date_anchor": getattr(investigation, "date_anchor", None),
            "last_event": dict(getattr(investigation, "last_event", None) or {}),
            "evidence": dict(getattr(investigation, "evidence", None) or {}),
        }
