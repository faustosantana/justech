"""Speech-act detection for Investigation Workspace (deterministic MVP)."""

from __future__ import annotations

import re

from app.lottery.ai.investigation_workspace.schemas import (
    AssetFilters,
    AssetPagination,
    AssetSort,
    WorkspaceActionDecision,
)
from app.lottery.ai.official_lottery_scope import canonicalize_lottery_name


_SHOW = re.compile(
    r"("
    r"mu[eé]stra(me)?\s+(esos?\s+)?resultados|"
    r"mu[eé]stra(me)?\s+(las\s+)?fechas(\s+de\s+coinciden\w*)?|"
    r"mostrar(me)?\s+(esos?\s+)?(resultados|coincidencias|todas|fechas)|"
    r"ens[eé][nñ]a(me)?\s+(la\s+)?tabla|"
    r"[aá]bre(lo|la)?(\s+(la\s+)?tabla|\s+esos?\s+resultados)?|"
    r"ver\s+(la\s+)?tabla|"
    r"ver\s+(las\s+)?(fechas|coincidencias|resultados)(\s+de\s+coinciden\w*)?|"
    r"dame\s+(la\s+)?tabla|"
    r"dame\s+(las\s+)?fechas|"
    r"lista(me)?\s+(las\s+)?(coincidencias|filas|resultados|fechas)|"
    r"crea(r)?\s+(una\s+)?tabla|"
    r"mostrar\s+todas|"
    r"ver\s+coincidencias|"
    r"mostrar\s+resultados"
    r")",
    re.I,
)
_SHOW_DATES = re.compile(
    r"("
    r"mu[eé]stra(me)?\s+(las\s+)?fechas|"
    r"ver\s+(las\s+)?fechas|"
    r"mostrar(me)?\s+(las\s+)?fechas|"
    r"dame\s+(las\s+)?fechas|"
    r"lista(me)?\s+(las\s+)?fechas"
    r")",
    re.I,
)
# Position breakdown / group view → sort by position columns (table transform).
_BREAKDOWN = re.compile(
    r"("
    r"desglos(ar|a|e)?(\s+por\s+posici\w*)?|"
    r"agrup(ar|a|e)?\s+por\s+posici\w*"
    r")",
    re.I,
)
_FILTER_VERB = re.compile(r"\bfiltra(r)?\b", re.I)
_SOLO_LOTTERY = re.compile(r"^\s*solo\s+", re.I)
_REMOVE_FILTER = re.compile(
    r"("
    r"quita(r)?(\s+el\s+filtro)?(\s+de)?|"
    r"sin\s+filtro|"
    r"^\s*todas\s+las\s+loter"
    r")",
    re.I,
)
_SORT = re.compile(
    r"("
    r"ord[eé]na(los|las|lo|la|r)?|"
    r"m[aá]s\s+recientes?(\s+primero)?|"
    r"desde\s+la\s+m[aá]s\s+reciente|"
    r"m[aá]s\s+antigu[oa]s?\s+primero|"
    r"por\s+fecha|"
    r"por\s+frecuencia"
    r")",
    re.I,
)
_EXPORT = re.compile(
    r"("
    r"exporta(r)?(\s+a)?(\s+excel|\s+xlsx|\s+csv)?|"
    r"desc[aá]rga(lo|la)?|"
    r"genera(r)?\s+(el\s+)?(excel|csv)|"
    r"\bexcel\b|\bcsv\b"
    r")",
    re.I,
)
_PAGE = re.compile(
    r"("
    r"(dame|muestra(me)?|mostrar(me)?|ver)\s+(los\s+|las\s+)?(pr[oó]ximos|siguientes|primer[oa]s?)\s+(\d{1,3})|"
    r"p[aá]gina\s+(\d{1,3})|"
    r"ver\s+m[aá]s"
    r")",
    re.I,
)
_SUMMARIZE = re.compile(
    r"("
    r"resume\s+(esa\s+)?tabla|"
    r"ver\s+resumen|"
    r"vuelve\s+al\s+resumen"
    r")",
    re.I,
)
_ASSET_REF = re.compile(
    r"\b(tabla|resultados?|filas?|listado|coincidencias|excel|xlsx|exportaci[oó]n)\b",
    re.I,
)
# Analyst 2.1 factual turns — never workspace, even with an asset present.
_FACTUAL_BLOCK = re.compile(
    r"("
    r"[uú]ltimas?\s+\d{1,3}\b|"
    r"[uú]ltima\s+(vez|aparici|del\s+\d)|"
    r"cu[aá]ndo\s+(sali[oó]|apareci)|"
    r"\bcompar[ae]\b|"
    r"coincidieron|"
    r"han\s+salido|"
    r"ahora\s+en\s+todas\s+las\s+(posiciones|loter)|"
    r"solo\s+en\s+\d{4}|"
    r"\by\s+el\s+\d{1,2}\b"
    r")",
    re.I,
)
_ASC = re.compile(r"\b(ascendente|antigu[oa]s?\s+primero|de\s+menor\s+a\s+mayor)\b", re.I)
_DESC = re.compile(
    r"\b(descendente|recientes?\s+primero|de\s+mayor\s+a\s+menor)\b", re.I
)


def _extract_lottery(text: str) -> str | None:
    from app.services.lottery_intent import _extract_lotteries

    lots = _extract_lotteries(text or "") or []
    if lots:
        return canonicalize_lottery_name(str(lots[0])) or str(lots[0])
    m = re.search(
        r"\b(loteka|nacional|leidsa|real|gana\s*m[aá]s|new\s+york\s+\d{1,2}\s*[:.]?\s*\d{0,2})\b",
        text or "",
        re.I,
    )
    if m:
        return canonicalize_lottery_name(m.group(1)) or m.group(1)
    return None


def _is_explicit_boot(raw: str) -> bool:
    """Show/export/page boot phrases that may materialize without an existing asset."""
    if _SHOW.search(raw) or _SHOW_DATES.search(raw) or _EXPORT.search(raw) or _BREAKDOWN.search(raw):
        return True
    if _PAGE.search(raw):
        return True
    if _SORT.search(raw) and _ASSET_REF.search(raw):
        return True
    return False


def _bare_en_lottery(raw: str) -> bool:
    """«En Nacional.» without table/filter verb — Analyst filter_refine, not workspace."""
    if _FILTER_VERB.search(raw) or _ASSET_REF.search(raw):
        return False
    return bool(re.match(r"^\s*(y\s+)?(ahora\s+)?en\s+\S+", raw or "", re.I))


class WorkspaceSpeechActDetector:
    """Deterministic speech-act recognition for clear workspace phrases."""

    @classmethod
    def detect(
        cls,
        message: str,
        *,
        has_active_asset: bool,
        has_active_investigation: bool = False,
    ) -> WorkspaceActionDecision | None:
        raw = (message or "").strip()
        if not raw:
            return None

        if _FACTUAL_BLOCK.search(raw):
            return None
        if _bare_en_lottery(raw):
            return None

        explicit_boot = _is_explicit_boot(raw)
        # Gate: active asset OR explicit show/export/table boot — never investigation alone.
        if not has_active_asset and not explicit_boot:
            return None

        if _EXPORT.search(raw) and not re.search(r"explic|significa|por\s+qu[eé]", raw, re.I):
            return WorkspaceActionDecision(
                action="export_results",
                export_format="xlsx",
                requires_asset_load=True,
                requires_huawei=False,
                reason_code="export_xlsx",
            )

        if _SUMMARIZE.search(raw):
            if not has_active_asset and not _ASSET_REF.search(raw):
                return None
            return WorkspaceActionDecision(
                action="summarize_asset",
                requires_huawei=True,
                reason_code="summarize_asset",
            )

        page_m = _PAGE.search(raw)
        if page_m:
            nums = [int(x) for x in re.findall(r"\d{1,3}", raw)]
            n = nums[0] if nums else 20
            if re.search(r"p[aá]gina", raw, re.I):
                if not has_active_asset:
                    return None
                return WorkspaceActionDecision(
                    action="paginate_results",
                    pagination=AssetPagination(page=max(1, n), page_size=20),
                    reason_code="paginate_page",
                )
            if re.search(r"primer", raw, re.I):
                return WorkspaceActionDecision(
                    action="paginate_results",
                    pagination=AssetPagination(page=1, page_size=max(1, min(n, 100))),
                    reason_code="paginate_first_n",
                )
            return WorkspaceActionDecision(
                action="paginate_results",
                pagination=AssetPagination(page=1, page_size=max(1, min(n, 100))),
                reason_code="paginate_next",
            )

        if _BREAKDOWN.search(raw):
            if not has_active_asset and not explicit_boot:
                return None
            return WorkspaceActionDecision(
                action="sort_results",
                sort=AssetSort(field="posicion_a_num", direction="asc"),
                requires_asset_load=True,
                reason_code="breakdown_by_position",
            )

        if _SORT.search(raw):
            if not has_active_asset:
                return None
            direction = "asc" if _ASC.search(raw) else "desc"
            if re.search(r"antigu", raw, re.I):
                direction = "asc"
            if re.search(r"recient", raw, re.I):
                direction = "desc"
            field = "fecha"
            if re.search(r"frecuen", raw, re.I):
                field = "fecha"  # frequency not a column; keep chronological table
            elif re.search(r"loter", raw, re.I):
                field = "loteria"
            elif re.search(r"posici", raw, re.I):
                field = "posicion_a_num"
            elif re.search(r"n[uú]mero", raw, re.I):
                field = "numero_a"
            return WorkspaceActionDecision(
                action="sort_results",
                sort=AssetSort(field=field, direction=direction),  # type: ignore[arg-type]
                reason_code="sort_results",
            )

        # Clear / abbreviated filters — require active asset (WA12–WA14).
        if has_active_asset and _REMOVE_FILTER.search(raw) and not _FILTER_VERB.search(raw):
            if re.search(r"ahora\s+en\s+todas", raw, re.I):
                return None
            return WorkspaceActionDecision(
                action="filter_results",
                filters=AssetFilters(),
                reason_code="clear_filters",
            )

        if has_active_asset and (
            _FILTER_VERB.search(raw)
            or (_SOLO_LOTTERY.search(raw) and _extract_lottery(raw))
            or (
                _ASSET_REF.search(raw)
                and _extract_lottery(raw)
                and re.search(r"\b(solo|filtra|en)\b", raw, re.I)
            )
        ):
            lot = _extract_lottery(raw)
            return WorkspaceActionDecision(
                action="filter_results",
                filters=AssetFilters(lottery=lot),
                requires_sql=False,
                reason_code="filter_lottery" if lot else "filter_clearish",
            )

        # «Solo Loteka.» / bare lottery name — only with active asset, no new subject digits.
        if has_active_asset:
            lot_only = _extract_lottery(raw)
            if (
                lot_only
                and len(raw) < 40
                and not re.search(r"\d{1,2}", raw)
                and not re.search(r"coincid|cu[aá]nt|sali[oó]|compar", raw, re.I)
            ):
                if re.search(r"\b(solo|en)\b", raw, re.I) or re.match(
                    r"^\s*(loteka|nacional|leidsa|real|gana)", raw, re.I
                ):
                    if _bare_en_lottery(raw):
                        return None
                    return WorkspaceActionDecision(
                        action="filter_results",
                        filters=AssetFilters(lottery=lot_only),
                        reason_code="filter_lottery_bare",
                    )

        if _SHOW.search(raw) or _SHOW_DATES.search(raw):
            if _SHOW_DATES.search(raw):
                return WorkspaceActionDecision(
                    action="show_dates",
                    requires_asset_load=True,
                    requires_huawei=False,
                    reason_code="show_dates",
                )
            return WorkspaceActionDecision(
                action="show_results",
                requires_asset_load=True,
                requires_huawei=False,
                reason_code="show_results",
            )

        return None
