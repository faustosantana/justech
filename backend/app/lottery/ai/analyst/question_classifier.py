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
        r"qu[eé]\s+ocurri[oó]\s+despu[eé]s|comportamiento\s+posterior|"
        r"d[ií]as?\s+siguientes|siguientes\s+a\s+cada|"
        r"qu[eé]\s+pas[oó]\s+en\s+los\s+.+\s+siguientes)",
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
        r"cu[aá]ndo\s+sali[oó]|cuando\s+sali[oó]|"
        r"cu[aá]ndo\s+apareci[oó]|cuando\s+apareci[oó]|"
        r"[uú]ltima\s+del?\b|[uú]ltimas?\s+del?\b|"
        r"[uú]ltima\s+vez|[uú]ltima\s+aparici[oó]n)",
        re.I,
    )
    _LAST_N = re.compile(
        r"\b(y\s+)?(las?\s+)?([uú]ltimas?|anteriores?)\s+"
        r"(\d{1,2}|una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|quince|veinte)"
        r"(\s+(veces|apariciones|sorteos))?\b|"
        r"\b(dame\s+)?(las?\s+)?(\d{1,2}|tres|cinco|diez)\s+anteriores?\b|"
        r"\b(una|un|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez)\s+"
        r"([uú]ltimas?|anteriores?)\b|"
        r"\b(\d{1,2})\s+([uú]ltimas|anteriores)\b",
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
        # Drop quantity digits mistaken as subjects
        from app.lottery.ai.turn_policy import (
            asks_all_lotteries,
            asks_all_positions,
            exclude_limit_from_subjects,
            extract_occurrence_limit,
            extract_other_occurrence_limit,
            is_correction_or_meta_request,
            is_most_recent_request,
            is_other_occurrences_request,
            is_previous_occurrences_request,
        )

        lim_pre = resolution.get("limit") or extract_occurrence_limit(raw)
        nums = exclude_limit_from_subjects(nums, lim_pre)
        # Lotteries named in this turn only — do not sticky-fill for last_times below
        named_lots = list(resolution.get("lotteries") or [])
        inherit_lot = False
        if not named_lots and (state.active_filters or {}).get("lottery_explicit"):
            # B.2: inherit the explicit filter lottery, never a polluted multi sticky list
            single = (state.active_filters or {}).get("lottery")
            if single:
                named_lots = [str(single)]
            else:
                named_lots = list(state.active_lotteries or [])[:4]
            inherit_lot = bool(named_lots)
        if asks_all_lotteries(raw):
            named_lots = []
            inherit_lot = False
        lots = named_lots or list(state.active_lotteries or [])
        years = [int(y) for y in cls._YEAR.findall(raw)]
        windows = sorted({int(x) for x in cls._D_WIN.findall(raw)}) or [1, 3, 7]
        pos_scope = resolution.get("position_scope")
        if asks_all_positions(raw):
            pos_scope = "all"
        elif pos_scope is None:
            pos_scope = state.active_position or state.last_position_scope
        params: dict[str, Any] = {
            "numbers": nums,
            "lotteries": lots[:4],
            "years": years,
            "windows": windows,
            "year_filter": resolution.get("year_filter") or (state.active_filters or {}).get("year"),
            "position_scope": pos_scope,
            "compare_with": resolution.get("compare_with"),
            "follow_up_kind": resolution.get("follow_up_kind"),
            "active_pair": list(getattr(state, "active_pair", None) or [])[:2],
            "use_active_pair": bool(resolution.get("use_active_pair")),
            "lottery_explicit": bool(
                named_lots or resolution.get("lottery_filter") or inherit_lot
            )
            and not asks_all_lotteries(raw),
            "lottery_filter": resolution.get("lottery_filter"),
            "position_explicit": bool(
                resolution.get("position_explicit")
                or (state.active_filters or {}).get("position_explicit")
            )
            and not asks_all_positions(raw),
            "primary": state.current_primary_candidate,
            "offset": resolution.get("offset"),
            "replay_last_intent": resolution.get("replay_last_intent"),
            "windows": list(resolution.get("windows") or windows),
        }

        # Same-day coincidence — before compare / complete-analysis paths
        from app.lottery.ai.same_day_coincidence import is_same_day_coincidence_question

        if is_same_day_coincidence_question(raw) or (
            resolution.get("active_relation") == "same_day"
            and resolution.get("follow_up_kind") in {None, "lotteries", "positions", "filtered"}
            and len(nums) >= 2
        ):
            sd = dict(params)
            sd["relation"] = "same_day"
            sd["active_relation"] = "same_day"
            sd["numbers"] = nums[:2] if len(nums) >= 2 else list(
                getattr(state, "active_pair", None) or state.active_numbers or []
            )[:2]
            sd["use_active_pair"] = True
            return ResearchQuestion("coincidences_only", sd, raw_message=raw)

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
        ) or re.search(
            r"comp[aá]ra(me|r|lo|la)?\s+(el\s+)?\d{1,2}\s+(con|y|vs|versus)\s+(el\s+)?\d{1,2}",
            raw,
            re.I,
        ):
            if resolution.get("compare_with") and nums:
                params["numbers"] = list(dict.fromkeys([*nums[:1], str(resolution["compare_with"])]))
            elif resolution.get("compare_with") and state.active_numbers:
                params["numbers"] = [
                    state.active_numbers[0],
                    str(resolution["compare_with"]),
                ]
            elif len(nums) >= 2:
                params["numbers"] = nums[:2]
            elif len(state.active_numbers or []) >= 2 and resolution.get("follow_up_kind") == "compare":
                params["numbers"] = list(state.active_numbers[:2])
            return ResearchQuestion("compare_numbers", params, raw_message=raw)

        # Year / position refinements while compare is active
        if (
            state.last_intent in {"compare_numbers", "compare"}
            or (state.active_filters or {}).get("compare_active")
        ) and (
            resolution.get("year_filter")
            or asks_all_positions(raw)
            or resolution.get("position_explicit")
            or re.search(r"\bsolo\s+en\s+20\d{2}\b|\ben\s+20\d{2}\b", raw, re.I)
            or re.search(r"primera\s+posici|m[aá]s\s+recientemente|cu[aá]l\s+de\s+los\s+dos", raw, re.I)
        ):
            cmp_nums = list(state.active_numbers[:2]) if len(state.active_numbers or []) >= 2 else nums
            if len(cmp_nums) < 2 and len(state.active_pair or []) >= 2:
                cmp_nums = list(state.active_pair[:2])
            if len(cmp_nums) >= 2:
                params["numbers"] = cmp_nums[:2]
                params["use_active_pair"] = True
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
            # Prefer temporal after windows over open investigation
            return ResearchQuestion("what_usually_happens_after", params, raw_message=raw)

        # last N / previous N / other N — BEFORE temporal_before (which matches «anteriores»)
        if (
            cls._LAST_N.search(raw)
            or resolution.get("follow_up_kind") == "last_n_occurrences"
            or resolution.get("limit")
            or is_previous_occurrences_request(raw)
            or is_other_occurrences_request(raw)
        ):
            lim = (
                resolution.get("limit")
                or extract_occurrence_limit(raw)
                or extract_other_occurrence_limit(raw)
                or 3
            )
            last_n_params = dict(params)
            last_n_params["limit"] = int(lim)
            # Inherit explicit lottery unless user cleared it
            if named_lots:
                last_n_params["lotteries"] = named_lots[:4]
                last_n_params["lottery_explicit"] = True
            elif inherit_lot and not asks_all_lotteries(raw):
                # Prefer the explicit single lottery filter (B.2), not a sticky multi list
                single = (state.active_filters or {}).get("lottery")
                if single:
                    last_n_params["lotteries"] = [str(single)]
                else:
                    last_n_params["lotteries"] = list(state.active_lotteries or [])[:4]
                last_n_params["lottery_explicit"] = True
            else:
                last_n_params["lotteries"] = []
                last_n_params["lottery_explicit"] = False
            if asks_all_positions(raw):
                last_n_params["position_scope"] = "all"
                last_n_params["position_explicit"] = True
            elif resolution.get("position_explicit") or (
                state.active_filters or {}
            ).get("position_explicit"):
                last_n_params["position_explicit"] = True
                last_n_params["position_scope"] = pos_scope
            if is_previous_occurrences_request(raw) or is_other_occurrences_request(raw):
                prior = int((state.last_analysis or {}).get("limit") or 0)
                last_n_params["offset"] = prior if prior > 0 else int(
                    resolution.get("offset") or 0
                )
                # Fetch prior+N then caller/tool slices; request enough rows
                last_n_params["limit"] = int(lim) + max(prior, 0)
                last_n_params["page_offset"] = prior
                last_n_params["result_limit"] = int(lim)
            subject = exclude_limit_from_subjects(
                nums[:1] if nums else list(state.active_numbers[:1]),
                int(lim),
            )
            if subject:
                last_n_params["numbers"] = subject[:1]
                last_n_params["active_pair"] = []
                last_n_params["use_active_pair"] = False
            elif state.active_numbers:
                last_n_params["numbers"] = list(state.active_numbers[:1])
            return ResearchQuestion("last_n_occurrences", last_n_params, raw_message=raw)

        # temporal_before only for calendar D− windows, not «anteriores a esas»
        if resolution.get("follow_up_kind") == "before" or (
            cls._TEMPORAL_BEFORE.search(raw)
            and not cls._AFTER.search(raw)
            and not is_previous_occurrences_request(raw)
            and not cls._LAST_N.search(raw)
        ):
            return ResearchQuestion("temporal_before", params, raw_message=raw)
        if cls._TEMPORAL_AFTER.search(raw) and re.search(r"d\s*\+", raw, re.I):
            return ResearchQuestion("temporal_windows", params, raw_message=raw)

        # Correction / meta: replay last factual intent with new subject
        if is_correction_or_meta_request(raw) and (nums or state.active_numbers):
            if nums:
                params["numbers"] = nums[:1]
            replay = state.last_intent or "last_times"
            if replay in {"last_n_occurrences", "last_occurrence", "last_times", None, ""}:
                return ResearchQuestion("last_times", params, raw_message=raw)
            if replay == "compare_numbers" and len(state.active_numbers or []) >= 2:
                params["numbers"] = list(state.active_numbers[:2])
                return ResearchQuestion("compare_numbers", params, raw_message=raw)
            return ResearchQuestion("last_times", params, raw_message=raw)

        if is_most_recent_request(raw) and (nums or state.active_numbers):
            # Same lottery-scope rule as _LAST_TIMES: sticky active_lotteries must not
            # become an implicit 4-lottery filter when the user did not name one.
            last_params = cls._last_times_lottery_params(
                params,
                named_lots=named_lots,
                inherit_lot=inherit_lot,
                resolution=resolution,
                raw=raw,
                state=state,
                nums=nums,
                lim_pre=lim_pre,
            )
            return ResearchQuestion("last_times", last_params, raw_message=raw)

        if cls._LAST_TIMES.search(raw) or resolution.get("follow_up_kind") == "last_occurrence":
            # Pair / "qué pasó las últimas veces que salieron A y B" → posterior behavior,
            # not a single-number last-occurrence lookup.
            if len(nums) >= 2 and re.search(
                r"(qu[eé]\s+pas|salieron|pareja|comportamiento|casos?)",
                raw,
                re.I,
            ) and not is_same_day_coincidence_question(raw):
                return ResearchQuestion(
                    "what_usually_happens_after", params, raw_message=raw
                )
            last_params = cls._last_times_lottery_params(
                params,
                named_lots=named_lots,
                inherit_lot=inherit_lot,
                resolution=resolution,
                raw=raw,
                state=state,
                nums=nums,
                lim_pre=lim_pre,
            )
            return ResearchQuestion("last_times", last_params, raw_message=raw)
        if cls._RELATED.search(raw):
            return ResearchQuestion("related_numbers", params, raw_message=raw)
        if cls._BEST_GROUP.search(raw):
            return ResearchQuestion("best_historical_group", params, raw_message=raw)
        # Frequency before open investigation when asking «cuántas veces»
        if cls._FREQUENCY.search(raw):
            return ResearchQuestion("frequency_behavior", params, raw_message=raw)
        # ANALYZE / open investigation
        if cls._OPEN.search(raw) and (nums or state.active_numbers or state.active_pair):
            # Soft «análisis más profundo» with active subject → deepen last_times/frequency
            if is_correction_or_meta_request(raw) and state.active_numbers:
                return ResearchQuestion("frequency_behavior", params, raw_message=raw)
            return ResearchQuestion("open_investigation", params, raw_message=raw)
        # Lottery-only filter in chain
        if re.search(r"\b(solamente|solo|ahora)\s+(nacional|loteka|leidsa|real)\b", raw, re.I) and (
            nums or state.active_numbers
        ):
            return ResearchQuestion("filtered_follow_up", params, raw_message=raw)
        if asks_all_lotteries(raw) and (nums or state.active_numbers):
            params["lottery_explicit"] = False
            params["lotteries"] = []
            if state.last_intent == "last_n_occurrences":
                params["limit"] = int((state.last_analysis or {}).get("limit") or 3)
                return ResearchQuestion("last_n_occurrences", params, raw_message=raw)
            return ResearchQuestion("last_times", params, raw_message=raw)
        if asks_all_positions(raw) and (nums or state.active_numbers):
            params["position_scope"] = "all"
            params["position_explicit"] = True
            if state.last_intent == "last_n_occurrences" or (state.last_analysis or {}).get("limit"):
                params["limit"] = int((state.last_analysis or {}).get("limit") or 3)
                return ResearchQuestion("last_n_occurrences", params, raw_message=raw)
            return ResearchQuestion("last_times", params, raw_message=raw)
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

        # Subject resume / bare statement / return_to without other intent
        # → default last_times research (never soft menu when the ball is known).
        if (
            resolution.get("follow_up_kind") == "last_occurrence"
            or resolution.get("return_to_number")
            or resolution.get("clear_compare")
        ) and (nums or state.active_numbers or resolution.get("numbers")):
            last_params = cls._last_times_lottery_params(
                params,
                named_lots=named_lots,
                inherit_lot=inherit_lot,
                resolution=resolution,
                raw=raw,
                state=state,
                nums=nums or list(resolution.get("numbers") or state.active_numbers or [])[:1],
                lim_pre=lim_pre,
            )
            return ResearchQuestion("last_times", last_params, raw_message=raw)

        return None

    @classmethod
    def _last_times_lottery_params(
        cls,
        params: dict[str, Any],
        *,
        named_lots: list[str],
        inherit_lot: bool,
        resolution: dict[str, Any],
        raw: str,
        state: ConversationState,
        nums: list[str],
        lim_pre: Any,
    ) -> dict[str, Any]:
        """Build last_times params without sticky multi-lottery truncation."""
        from app.lottery.ai.turn_policy import asks_all_lotteries, exclude_limit_from_subjects

        last_params = dict(params)
        if named_lots or inherit_lot:
            last_params["lotteries"] = (named_lots or list(state.active_lotteries or []))[:4]
            last_params["lottery_explicit"] = True
        else:
            # Unscoped: empty list → planner uses DEFAULT_ALL_HISTORY_LOTTERIES
            last_params["lotteries"] = []
            last_params["lottery_explicit"] = bool(
                named_lots or resolution.get("lottery_filter")
            )
        if asks_all_lotteries(raw):
            last_params["lotteries"] = []
            last_params["lottery_explicit"] = False
        if nums:
            last_params["numbers"] = exclude_limit_from_subjects(
                nums[:1] if len(nums) == 1 else nums, lim_pre
            )
            last_params["active_pair"] = []
            last_params["use_active_pair"] = False
        return last_params

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
