"""Research question classification (Fase B) — open investigations only.

Does NOT touch motor math. Maps natural language to research kinds that
drive dynamic plans over existing Lottery Tools.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.lottery.ai.conversation_state import ConversationState


@dataclass
class ResearchQuestion:
    """High-level investigation question for the Research Engine."""

    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    requires_discovery: bool = False
    raw_message: str = ""
    confidence_hint: str | None = None


# Kinds handled by Research Engine (Fase B). Discovery kinds stay reserved.
RESEARCH_KINDS = (
    "what_usually_happens_after",
    "which_lottery_confirms_first",
    "which_confirms_most",
    "related_numbers",
    "best_historical_group",
    "compare_numbers",
    "compare_groups",
    "compare_lotteries",
    "compare_positions",
    "compare_periods",
    "case_search",
    "temporal_after",
    "temporal_before",
    "temporal_windows",
    "last_times",
    "last_n_occurrences",
    "frequency_behavior",
    "coincidences_only",
    "confirmations_only",
    "equivalents_only",
    "recent_cases_only",
    "filtered_follow_up",
    "open_investigation",
)


class QuestionClassifier:
    """Classify open research questions without inventing facts."""

    _AFTER = re.compile(
        r"(qu[eé]\s+suele\s+pasar\s+despu[eé]s|qu[eé]\s+pasa\s+despu[eé]s|"
        r"despu[eé]s\s+de\s+(esta\s+)?(combinaci[oó]n|pareja|n[uú]mero)|"
        r"qu[eé]\s+ocurri[oó]\s+despu[eé]s|comportamiento\s+posterior)",
        re.I,
    )
    _CONFIRM_FIRST = re.compile(
        r"(loter[ií]a\s+confirma\s+primero|cu[aá]l\s+confirma\s+primero|"
        r"qui[eé]n\s+confirma\s+primero|confirma\s+antes)",
        re.I,
    )
    _CONFIRM_MOST = re.compile(
        r"(cu[aá]l\s+confirma\s+m[aá]s|confirma\s+m[aá]s|m[aá]s\s+confirmaciones|"
        r"mayor\s+confirmaci[oó]n)",
        re.I,
    )
    _RELATED = re.compile(
        r"(n[uú]meros?\s+m[aá]s\s+relacionad|relacionados?\s+con|"
        r"compa[nñ]eros|vecinos\s+hist)",
        re.I,
    )
    _BEST_GROUP = re.compile(
        r"(grupo\s+.*(mejor|mejor\s+comportamiento)|mejor\s+comportamiento|"
        r"mejor\s+grupo|tabla\s*1\s+.*grupo)",
        re.I,
    )
    _COMPARE_NUM = re.compile(
        r"(comp[aá]ra(me|r|lo|la)?(\s+con)?\s+(estos\s+)?(dos\s+)?n[uú]meros|"
        r"comp[aá]ra(me|r|lo|la)?(\s+con)?\s+(el\s+)?\d{1,2}\s+(y|vs|versus|con)\s+(el\s+)?\d{1,2}|"
        r"comp[aá]ra(me|r|lo|la)?\s+con\s+(el\s+)?\d{1,2}|"
        r"\d{1,2}\s+vs\s+\d{1,2}|diferencias?\s+entre\s+(el\s+)?\d{1,2}|"
        r"comportamiento\s+hist[oó]rico\s+del?\s+\d{1,2}\s+y)",
        re.I,
    )
    _COMPARE_GROUP = re.compile(
        r"(comp[aá]ra(me|r)?\s+(estos\s+)?(dos\s+)?grupos|"
        r"grupo\s+.+\s+vs\s+grupo|tabla\s*1\s+a\s+vs)",
        re.I,
    )
    _COMPARE_LOT = re.compile(
        r"(diferencias?\s+entre\s+\w+\s+y\s+\w+|comp[aá]ra(me|r)?\s+\w+\s+y\s+\w+|"
        r"nacional\s+(vs|versus|y)\s+loteka|loteka\s+(vs|versus|y)\s+nacional)",
        re.I,
    )
    _COMPARE_POS = re.compile(
        r"(primera\s+vs\s+segunda|1(ra)?\s+vs\s+2(da)?|"
        r"comp[aá]ra(r)?\s+posiciones)",
        re.I,
    )
    _COMPARE_PERIOD = re.compile(
        r"(20\d{2}\s+(vs|versus|y)\s+20\d{2}|a[nñ]o\s+20\d{2}\s+vs|"
        r"comp[aá]ra(r)?\s+(per[ií]odos|a[nñ]os))",
        re.I,
    )
    _CASE_SEARCH = re.compile(
        r"(casos?\s+(equivalentes|similares|parecidos|relacionados)|"
        r"buscar\s+casos|mu[eé]strame\s+todas\s+las\s+veces|"
        r"algo\s+parecido|casos?\s+parcialmente)",
        re.I,
    )
    _LAST_TIMES = re.compile(
        r"(ultimas?\s+veces|qu[eé]\s+ocurri[oó]\s+las\s+[uú]ltimas|"
        r"las\s+[uú]ltimas\s+veces|(?<!\d\s)recientes(?!\s+\d)|"
        r"cu[aá]ndo\s+sali[oó]|cuando\s+sali[oó])",
        re.I,
    )
    _LAST_N = re.compile(
        r"\b(y\s+)?(las?\s+)?([uú]ltimas?|anteriores?)\s+"
        r"(\d{1,2}|una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte)"
        r"(\s+(veces|apariciones|sorteos))?\b|"
        r"\b(dame\s+)?(las?\s+)?(\d{1,2}|tres|cinco|diez)\s+anteriores?\b",
        re.I,
    )
    _TEMPORAL_AFTER = re.compile(
        r"\b(despu[eé]s|d\s*\+\s*(1|3|7|15|30)|hasta\s+d\s*\+)\b",
        re.I,
    )
    _TEMPORAL_BEFORE = re.compile(r"\b(antes|previo|anterior(es)?)\b", re.I)
    _COINCIDENCES = re.compile(r"\b(coincidencias?|solamente\s+coincidencias)\b", re.I)
    _CONFIRMATIONS = re.compile(
        r"\b(solamente\s+confirmaciones|solo\s+confirmaciones|confirmaciones\s+cruzadas)\b",
        re.I,
    )
    _EQUIV_ONLY = re.compile(
        r"\b(solamente\s+casos\s+equivalentes|solo\s+equivalentes|"
        r"casos\s+equivalentes)\b",
        re.I,
    )
    _RECENT_ONLY = re.compile(
        r"\b(casos\s+recientes|solamente\s+recientes|solo\s+recientes)\b",
        re.I,
    )
    _FREQUENCY = re.compile(r"\b(frecuencia|frecuencias|cu[aá]ntas?\s+veces)\b", re.I)
    _OPEN = re.compile(
        r"(investiga|analiza(\s+\w+){0,4}\s+(el\s+)?\d|"
        r"analiza\s+(en\s+profundidad|completa(mente)?|el\s+comportamiento)|"
        r"haz(me)?\s+un\s+(estudio|an[aá]lisis)|estudia(r)?\s+(el\s+)?\d|"
        r"investiga(r)?\s+(el\s+)?(grupo\s+(del\s+)?)?\d|"
        r"comportamiento\s+hist|"
        r"qu[eé]\s+suele|buscar\s+comportamientos)",
        re.I,
    )
    _NUM = re.compile(r"\b(\d{1,2})\b")
    _YEAR = re.compile(r"\b(20\d{2})\b")
    _D_WIN = re.compile(r"[dD]\s*\+\s*(1|3|7|15|30)")

    @classmethod
    def classify(
        cls,
        message: str,
        state: ConversationState,
        resolution: dict[str, Any] | None = None,
    ) -> ResearchQuestion | None:
        resolution = resolution or {}
        raw = message or ""
        nums = cls._extract_numbers(raw, state, resolution)
        # Lotteries named in this turn only — do not sticky-fill for last_times below
        named_lots = list(resolution.get("lotteries") or [])
        lots = named_lots or list(state.active_lotteries or [])
        years = [int(y) for y in cls._YEAR.findall(raw)]
        windows = sorted({int(x) for x in cls._D_WIN.findall(raw)}) or [1, 3, 7]
        params: dict[str, Any] = {
            "numbers": nums,
            "lotteries": lots[:4],
            "years": years,
            "windows": windows,
            "year_filter": resolution.get("year_filter") or (state.active_filters or {}).get("year"),
            "position_scope": resolution.get("position_scope")
            or state.active_position
            or state.last_position_scope,
            "compare_with": resolution.get("compare_with"),
            "follow_up_kind": resolution.get("follow_up_kind"),
            "active_pair": list(getattr(state, "active_pair", None) or [])[:2],
            "use_active_pair": bool(resolution.get("use_active_pair")),
            "lottery_explicit": bool(named_lots or resolution.get("lottery_filter")),
            "lottery_filter": resolution.get("lottery_filter"),
            "primary": state.current_primary_candidate,
        }

        if cls._CONFIRM_FIRST.search(raw):
            return ResearchQuestion("which_lottery_confirms_first", params, raw_message=raw)
        if cls._CONFIRM_MOST.search(raw):
            return ResearchQuestion("which_confirms_most", params, raw_message=raw)
        if cls._COMPARE_GROUP.search(raw):
            return ResearchQuestion("compare_groups", params, raw_message=raw)
        if cls._COMPARE_POS.search(raw):
            return ResearchQuestion("compare_positions", params, raw_message=raw)
        if cls._COMPARE_PERIOD.search(raw) or (
            len(years) >= 2 and re.search(r"\b(vs|versus|compa)", raw, re.I)
        ):
            return ResearchQuestion("compare_periods", params, raw_message=raw)
        if cls._COMPARE_LOT.search(raw) and len(lots) >= 2:
            return ResearchQuestion("compare_lotteries", params, raw_message=raw)
        if cls._COMPARE_NUM.search(raw) or (
            resolution.get("follow_up_kind") == "compare" and (nums or resolution.get("compare_with"))
        ):
            if resolution.get("compare_with") and nums:
                params["numbers"] = list(dict.fromkeys([*nums[:1], str(resolution["compare_with"])]))
            elif resolution.get("compare_with") and state.active_numbers:
                params["numbers"] = [
                    state.active_numbers[0],
                    str(resolution["compare_with"]),
                ]
            return ResearchQuestion("compare_numbers", params, raw_message=raw)
        if cls._EQUIV_ONLY.search(raw):
            return ResearchQuestion("equivalents_only", params, raw_message=raw)
        if cls._CONFIRMATIONS.search(raw):
            return ResearchQuestion("confirmations_only", params, raw_message=raw)
        if cls._COINCIDENCES.search(raw):
            return ResearchQuestion("coincidences_only", params, raw_message=raw)
        if cls._RECENT_ONLY.search(raw):
            return ResearchQuestion("recent_cases_only", params, raw_message=raw)
        if cls._CASE_SEARCH.search(raw) or resolution.get("follow_up_kind") in {
            "group",
        }:
            return ResearchQuestion("case_search", params, raw_message=raw)
        if cls._AFTER.search(raw) or (
            resolution.get("follow_up_kind") == "after" and (nums or state.active_numbers)
        ):
            return ResearchQuestion("what_usually_happens_after", params, raw_message=raw)
        if resolution.get("follow_up_kind") == "before" or (
            cls._TEMPORAL_BEFORE.search(raw) and not cls._AFTER.search(raw)
        ):
            return ResearchQuestion("temporal_before", params, raw_message=raw)
        if cls._TEMPORAL_AFTER.search(raw) and re.search(r"d\s*\+", raw, re.I):
            return ResearchQuestion("temporal_windows", params, raw_message=raw)
        # last N follow-up before generic last_times
        if (
            cls._LAST_N.search(raw)
            or resolution.get("follow_up_kind") == "last_n_occurrences"
            or resolution.get("limit")
        ):
            from app.lottery.ai.turn_policy import extract_occurrence_limit

            lim = resolution.get("limit") or extract_occurrence_limit(raw) or 3
            last_n_params = dict(params)
            last_n_params["limit"] = int(lim)
            last_n_params["lotteries"] = named_lots[:4]
            last_n_params["lottery_explicit"] = bool(
                named_lots or resolution.get("lottery_filter")
            )
            last_n_params["position_explicit"] = bool(resolution.get("position_explicit"))
            if nums:
                last_n_params["numbers"] = nums[:1] if len(nums) == 1 else nums
                last_n_params["active_pair"] = []
                last_n_params["use_active_pair"] = False
            elif state.active_numbers:
                last_n_params["numbers"] = list(state.active_numbers[:1])
            return ResearchQuestion("last_n_occurrences", last_n_params, raw_message=raw)
        if cls._LAST_TIMES.search(raw) or resolution.get("follow_up_kind") == "last_occurrence":
            # Pair / "qué pasó las últimas veces que salieron A y B" → posterior behavior,
            # not a single-number last-occurrence lookup.
            if len(nums) >= 2 and re.search(
                r"(qu[eé]\s+pas|salieron|pareja|comportamiento|casos?)",
                raw,
                re.I,
            ):
                return ResearchQuestion(
                    "what_usually_happens_after", params, raw_message=raw
                )
            # Last-occurrence must not inherit sticky pair / sticky lottery as subject
            last_params = dict(params)
            last_params["lotteries"] = named_lots[:4]
            last_params["lottery_explicit"] = bool(
                named_lots or resolution.get("lottery_filter")
            )
            if nums:
                last_params["numbers"] = nums[:1] if len(nums) == 1 else nums
                last_params["active_pair"] = []
                last_params["use_active_pair"] = False
            return ResearchQuestion("last_times", last_params, raw_message=raw)
        if cls._RELATED.search(raw):
            return ResearchQuestion("related_numbers", params, raw_message=raw)
        if cls._BEST_GROUP.search(raw):
            return ResearchQuestion("best_historical_group", params, raw_message=raw)
        # ANALYZE / open investigation BEFORE frequency (Fase X)
        if cls._OPEN.search(raw) and (nums or state.active_numbers or state.active_pair):
            return ResearchQuestion("open_investigation", params, raw_message=raw)
        if cls._FREQUENCY.search(raw):
            return ResearchQuestion("frequency_behavior", params, raw_message=raw)
        # Lottery-only filter in chain
        if re.search(r"\b(solamente|solo|ahora)\s+(nacional|loteka|leidsa|real)\b", raw, re.I) and (
            nums or state.active_numbers
        ):
            return ResearchQuestion("filtered_follow_up", params, raw_message=raw)
        # Chained filters still research-worthy
        if resolution.get("follow_up_kind") in {
            "lotteries",
            "positions",
            "d_plus_1",
            "d_plus_3",
            "d_plus_7",
            "first_occurrence",
        } and (nums or state.active_numbers):
            return ResearchQuestion("filtered_follow_up", params, raw_message=raw)
        return None

    @classmethod
    def _extract_numbers(
        cls,
        raw: str,
        state: ConversationState,
        resolution: dict[str, Any],
    ) -> list[str]:
        from app.lottery.ai.turn_policy import extract_subject_numbers, strip_quantity_spans

        found = extract_subject_numbers(raw)
        if resolution.get("numbers"):
            found = [
                str(n).zfill(2) if str(n).isdigit() and len(str(n)) <= 2 else str(n)
                for n in resolution["numbers"]
            ] + [n for n in found if n not in {
                str(x).zfill(2) if str(x).isdigit() and len(str(x)) <= 2 else str(x)
                for x in resolution["numbers"]
            }]
        if not found and state.active_numbers:
            found = list(state.active_numbers)
        if not found and getattr(state, "active_pair", None):
            found = list(state.active_pair)
        out: list[str] = []
        for n in found:
            if n not in out and not (str(n).isdigit() and int(n) > 99):
                out.append(str(n).zfill(2) if str(n).isdigit() and len(str(n)) <= 2 else str(n))
        return out[:6]
