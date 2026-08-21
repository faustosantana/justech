"""Inteligencia histórica 360° — agrega adjudicaciones verificables del índice local.

No inventa datos. No usa LLM para cifras.
Prioriza award_date de contratos válidos (no última publicación).
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import mean, median
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_historical_award import DGCPHistoricalAward
from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.dgcp_historical_intelligence import (
    BudgetComparisonBlock,
    ConcentrationBlock,
    CurrentProcessBrief,
    DataQualitySummary,
    DGCPHistoricalIntelligenceResponse,
    ExecutiveSummaryBlock,
    FrequencyBlock,
    HistoricalPurchaseRow,
    HistoricalSourceRef,
    InstitutionProfileBlock,
    LastPurchaseBlock,
    LastSupplierBlock,
    ModalityStatsRow,
    PriceHistoryBlock,
    PricePoint,
    ProductLineHistory,
    SupplierRankRow,
)
from app.services.dgcp_historical_similarity_engine import (
    build_query_tokens,
    core_query_tokens,
    institution_matches_strict,
    is_valid_award_status,
    match_classification,
    match_classification_label,
    score_award,
)

logger = logging.getLogger(__name__)

UTC = timezone.utc

SCAN_LIMIT = 3500
RESULT_LIMIT = 80
SUPPLIER_RANK_LIMIT = 15
RELATED_LIMIT = 20

# Score → % aproximado para UI (acotado)
def _score_to_pct(score: float) -> float:
    return round(min(99.0, max(0.0, (score / 100.0) * 100.0)), 1)


def _dec(v: Any) -> Decimal | None:
    if v is None:
        return None
    try:
        d = Decimal(str(v))
        return d
    except Exception:
        return None


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _data_quality(
    *,
    supplier: str | None,
    amount: Decimal | None,
    award_date: datetime | None,
    process_code: str | None,
    unit_price: Decimal | None,
    quantity: Decimal | None,
) -> str:
    has_core = bool(supplier and amount and award_date and process_code)
    has_line = bool(unit_price and quantity and float(quantity) > 0)
    if has_core and has_line:
        return "VERIFICADO"
    if has_core:
        return "PARCIAL"
    return "INCOMPLETO"


class DGCPHistoricalIntelligenceService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    async def build_for_opportunity(
        self,
        opportunity_id: uuid.UUID,
        *,
        window_months: int | None = 24,
        limit: int = RESULT_LIMIT,
    ) -> DGCPHistoricalIntelligenceResponse:
        t0 = time.perf_counter()
        opp = await self._get_opportunity(opportunity_id)
        window_months = None if window_months in (0, None) else max(1, min(int(window_months), 120))

        query_tokens = build_query_tokens(
            opp.title,
            opp.description,
            opp.objeto_proceso,
            (opp.full_info or {}).get("objeto") if isinstance(opp.full_info, dict) else None,
        )
        core_tokens = core_query_tokens(opp.title, opp.description, opp.objeto_proceso)

        awards = await self._load_institution_awards(
            institution=opp.institution,
            institution_code=(opp.full_info or {}).get("codigo_unidad_compra")
            if isinstance(opp.full_info, dict)
            else None,
            window_months=window_months,
        )
        # Ampliar con matches de producto fuera de institución si hay pocos
        if len(awards) < 30 and core_tokens:
            extra = await self._load_keyword_awards(core_tokens, window_months=window_months)
            seen = {a.id for a in awards}
            for a in extra:
                if a.id not in seen:
                    awards.append(a)
                    seen.add(a.id)

        scored: list[tuple[DGCPHistoricalAward, float, list[str], str]] = []
        for award in awards:
            if not self._is_valid_purchase(award):
                continue
            search_blob = " ".join(
                filter(
                    None,
                    [
                        award.search_text,
                        award.item_description,
                        award.item_description_user,
                        award.contract_object,
                        award.process_code,
                    ],
                )
            )
            score, reasons = score_award(
                query_tokens=query_tokens or core_tokens,
                query_institution=opp.institution or "",
                query_objeto=opp.objeto_proceso,
                award_institution=award.buyer_institution or "",
                award_objeto=award.objeto_proceso,
                award_search_text=search_blob,
                same_institution_required=False,
            )
            same_inst = institution_matches_strict(
                opp.institution or "",
                award.buyer_institution or "",
                query_institution_code=(opp.full_info or {}).get("codigo_unidad_compra")
                if isinstance(opp.full_info, dict)
                else None,
                candidate_institution_code=award.buyer_institution_code,
            )
            if same_inst and score < 12:
                # Historial institucional puro (sin overlap de producto) — score base
                score = max(score, 18.0)
                reasons = reasons or ["Misma institución (historial)"]
            if score < 12 and not same_inst:
                continue
            exact = self._exact_item_match(core_tokens, search_blob)
            klass = match_classification(score, exact_item=exact)
            scored.append((award, score, reasons, klass))

        # Prefer same institution for "last purchase"
        same_inst_scored = [
            x
            for x in scored
            if institution_matches_strict(
                opp.institution or "",
                x[0].buyer_institution or "",
                query_institution_code=(opp.full_info or {}).get("codigo_unidad_compra")
                if isinstance(opp.full_info, dict)
                else None,
                candidate_institution_code=x[0].buyer_institution_code,
            )
        ]
        pool_for_last = same_inst_scored or scored
        # Última compra = max award_date entre válidas; prefer comparable (score alto)
        comparable = [x for x in pool_for_last if x[1] >= 35 or x[3] in ("EXACTA", "ALTA_SIMILITUD")]
        last_pool = comparable or pool_for_last
        last_pool_sorted = sorted(
            last_pool,
            key=lambda x: (
                x[0].award_date or datetime.min.replace(tzinfo=UTC),
                x[1],
            ),
            reverse=True,
        )

        last_purchase = self._build_last_purchase(last_pool_sorted)
        last_supplier = self._build_last_supplier(same_inst_scored or scored)

        institution_rows = [
            self._to_row(a, score, reasons, klass)
            for a, score, reasons, klass in sorted(
                same_inst_scored or scored,
                key=lambda x: x[0].award_date or datetime.min.replace(tzinfo=UTC),
                reverse=True,
            )[:limit]
        ]

        suppliers_ranking, concentration = self._suppliers_and_concentration(
            [x[0] for x in (same_inst_scored or scored)]
        )
        price_history = self._price_history(
            [x for x in (same_inst_scored or scored) if x[1] >= 35] or same_inst_scored or scored
        )
        frequency = self._frequency([x[0] for x in (same_inst_scored or scored)], window_months)
        modalities = self._modalities([x[0] for x in (same_inst_scored or scored)])
        related = [
            self._to_row(a, score, reasons, klass)
            for a, score, reasons, klass in sorted(scored, key=lambda x: x[1], reverse=True)[
                :RELATED_LIMIT
            ]
            if not institution_matches_strict(
                opp.institution or "",
                a.buyer_institution or "",
            )
            or score >= 45
        ]
        # Deduplicate related by process_code keeping best score
        related = self._dedupe_by_process(related)

        product_lines = self._product_lines(opp, scored)
        budget = self._budget_comparison(opp, last_purchase)
        inst_profile = self._institution_profile(
            opp.institution, [x[0] for x in (same_inst_scored or scored)], modalities
        )
        dq = self._quality_summary(institution_rows)
        summary = self._executive_summary(
            opp,
            last_purchase,
            suppliers_ranking,
            price_history,
            frequency,
            len({r.process_code for r in institution_rows}),
            window_months,
        )

        latency = (time.perf_counter() - t0) * 1000
        return DGCPHistoricalIntelligenceResponse(
            current_process=CurrentProcessBrief(
                opportunity_id=opp.id,
                process_code=opp.code,
                title=opp.title,
                institution=opp.institution,
                estimated_amount=_dec(opp.amount),
                currency=opp.currency or "DOP",
                modality=opp.modalidad,
                objeto_proceso=opp.objeto_proceso,
                status=opp.status,
                amount_kind="estimado",
            ),
            window_months=window_months,
            last_purchase=last_purchase,
            last_supplier=last_supplier,
            institution_purchases=institution_rows,
            suppliers_ranking=suppliers_ranking[:SUPPLIER_RANK_LIMIT],
            concentration=concentration,
            product_lines=product_lines,
            price_history=price_history,
            frequency=frequency,
            modalities=modalities,
            related_processes=related[:RELATED_LIMIT],
            budget_comparison=budget,
            institution_profile=inst_profile,
            executive_summary=summary,
            data_quality=dq,
            statistics={
                "valid_award_lines": len(scored),
                "same_institution_lines": len(same_inst_scored),
                "unique_processes": len({x[0].process_code for x in scored}),
                "unique_suppliers": len(
                    {x[0].supplier_name for x in scored if x[0].supplier_name}
                ),
                "cancelled_excluded": True,
            },
            latency_ms=round(latency, 1),
            indexed_lines_scanned=len(awards),
            message=(
                "Análisis sobre adjudicaciones/contratos indexados (fuente DGCP). "
                "Montos de proceso actual son estimados; históricos son adjudicados/contratados."
                if scored
                else "No hay adjudicaciones verificables indexadas para esta institución/producto en la ventana."
            ),
        )

    async def _get_opportunity(self, opportunity_id: uuid.UUID) -> DGCPOpportunity:
        row = (
            await self.db.execute(
                select(DGCPOpportunity).where(
                    DGCPOpportunity.id == opportunity_id,
                    DGCPOpportunity.tenant_id == self.tenant_id,
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise ValueError("Licitación no encontrada")
        return row

    def _is_valid_purchase(self, award: DGCPHistoricalAward) -> bool:
        if not award.contract_url and not award.awarded_amount:
            return False
        if not is_valid_award_status(award.award_status):
            return False
        if not award.award_date:
            return False
        return True

    @staticmethod
    def _exact_item_match(core_tokens: set[str], search_blob: str) -> bool:
        if len(core_tokens) < 2:
            return False
        award_tokens = build_query_tokens(search_blob)
        overlap = core_tokens & award_tokens
        return len(overlap) >= max(2, int(len(core_tokens) * 0.7))

    async def _load_institution_awards(
        self,
        *,
        institution: str,
        institution_code: Any,
        window_months: int | None,
    ) -> list[DGCPHistoricalAward]:
        filters = [DGCPHistoricalAward.tenant_id == self.tenant_id]
        if window_months:
            since = datetime.now(UTC) - timedelta(days=int(window_months) * 30)
            filters.append(DGCPHistoricalAward.award_date >= since)

        # Prefer code match; also name ilike
        code = str(institution_code).strip() if institution_code not in (None, "") else None
        name_norm = (institution or "").strip()
        inst_filters = []
        if code:
            inst_filters.append(DGCPHistoricalAward.buyer_institution_code == code)
        if name_norm:
            # Token-ish: first meaningful chunk
            token = name_norm.split()[0] if name_norm else ""
            if len(token) >= 4:
                inst_filters.append(DGCPHistoricalAward.buyer_institution.ilike(f"%{token}%"))
            inst_filters.append(DGCPHistoricalAward.buyer_institution.ilike(f"%{name_norm[:40]}%"))

        q = (
            select(DGCPHistoricalAward)
            .where(and_(*filters))
            .where(or_(*inst_filters) if inst_filters else True)
            .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
            .limit(SCAN_LIMIT)
        )
        rows = list((await self.db.execute(q)).scalars().all())
        # Strict filter in Python for institution
        return [
            r
            for r in rows
            if institution_matches_strict(
                institution or "",
                r.buyer_institution or "",
                query_institution_code=code,
                candidate_institution_code=r.buyer_institution_code,
            )
        ]

    async def _load_keyword_awards(
        self, core_tokens: set[str], *, window_months: int | None
    ) -> list[DGCPHistoricalAward]:
        if not core_tokens:
            return []
        filters = [DGCPHistoricalAward.tenant_id == self.tenant_id]
        if window_months:
            since = datetime.now(UTC) - timedelta(days=int(window_months) * 30)
            filters.append(DGCPHistoricalAward.award_date >= since)
        # Use top 3 longest tokens for ILIKE
        keys = sorted(core_tokens, key=len, reverse=True)[:3]
        text_filters = [DGCPHistoricalAward.search_text.ilike(f"%{k}%") for k in keys if len(k) >= 4]
        if not text_filters:
            return []
        q = (
            select(DGCPHistoricalAward)
            .where(and_(*filters))
            .where(or_(*text_filters))
            .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
            .limit(800)
        )
        return list((await self.db.execute(q)).scalars().all())

    def _to_row(
        self,
        award: DGCPHistoricalAward,
        score: float,
        reasons: list[str],
        klass: str,
    ) -> HistoricalPurchaseRow:
        pct = _score_to_pct(score)
        amount = _dec(award.awarded_amount) or _dec(award.total_line_amount)
        qty = _dec(award.quantity)
        unit = _dec(award.unit_price)
        # No inventar unit price si falta cantidad confiable
        if unit and qty is not None and float(qty) <= 0:
            unit = None
        rnc = None
        raw = award.raw_payload or {}
        if isinstance(raw, dict):
            rnc = raw.get("rnc") or raw.get("RNC") or (raw.get("extra") or {}).get("rnc")
        quality = _data_quality(
            supplier=award.supplier_name,
            amount=amount,
            award_date=award.award_date,
            process_code=award.process_code,
            unit_price=unit,
            quantity=qty,
        )
        return HistoricalPurchaseRow(
            award_id=str(award.id),
            process_code=award.process_code,
            contract_code=award.contract_code,
            award_date=_iso(award.award_date),
            institution=award.buyer_institution,
            description=award.item_description_user
            or award.item_description
            or award.contract_object,
            supplier_name=award.supplier_name,
            supplier_rpe=award.supplier_rpe,
            supplier_rnc=str(rnc) if rnc else None,
            awarded_amount=amount,
            currency=award.currency or "DOP",
            quantity=qty,
            unit_price=unit,
            unit_measure=award.unit_measure,
            modality=award.modality,
            award_status=award.award_status,
            match_class=klass,  # type: ignore[arg-type]
            match_class_label=match_classification_label(klass, similarity_pct=pct),
            similarity_score=round(score, 2),
            similarity_pct=pct,
            match_reasons=reasons[:6],
            data_quality=quality,  # type: ignore[arg-type]
            source=HistoricalSourceRef(
                source=award.source or "dgcp_contratos",
                source_url=award.contract_url or award.process_url,
                process_url=award.process_url,
                contract_url=award.contract_url,
                dgcp_process_code=award.process_code,
                retrieved_at=_iso(award.indexed_at),
            ),
        )

    def _build_last_purchase(
        self, sorted_pool: list[tuple[DGCPHistoricalAward, float, list[str], str]]
    ) -> LastPurchaseBlock:
        if not sorted_pool:
            return LastPurchaseBlock(
                available=False,
                title="Sin compra comparable verificable",
                caveats=["No hay adjudicación/contrato válido con fecha en el índice para este criterio."],
            )
        award, score, reasons, klass = sorted_pool[0]
        row = self._to_row(award, score, reasons, klass)
        pct = row.similarity_pct
        title = match_classification_label(klass, similarity_pct=pct)
        caveats: list[str] = []
        if klass != "EXACTA":
            caveats.append(
                "No se afirma igualdad exacta de producto; se muestra la compra comparable más reciente "
                "según similitud de texto/institución."
            )
        if not row.unit_price:
            caveats.append("Precio unitario no disponible o cantidad no confiable.")
        return LastPurchaseBlock(
            available=True,
            title=title,
            match_class=klass,  # type: ignore[arg-type]
            match_class_label=title,
            criterion="; ".join(reasons[:4]) if reasons else "Fecha de adjudicación + similitud",
            purchase=row,
            caveats=caveats,
        )

    def _build_last_supplier(
        self, scored: list[tuple[DGCPHistoricalAward, float, list[str], str]]
    ) -> LastSupplierBlock:
        dated = sorted(
            [x for x in scored if x[0].supplier_name and x[0].award_date],
            key=lambda x: x[0].award_date or datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        if not dated:
            return LastSupplierBlock(available=False)
        a = dated[0][0]
        return LastSupplierBlock(
            available=True,
            supplier_name=a.supplier_name,
            supplier_rpe=a.supplier_rpe,
            award_date=_iso(a.award_date),
            awarded_amount=_dec(a.awarded_amount) or _dec(a.total_line_amount),
            currency=a.currency or "DOP",
            process_code=a.process_code,
            source_url=a.contract_url or a.process_url,
        )

    def _suppliers_and_concentration(
        self, awards: list[DGCPHistoricalAward]
    ) -> tuple[list[SupplierRankRow], ConcentrationBlock]:
        by_sup: dict[str, dict[str, Any]] = {}
        total_amount = Decimal("0")
        for a in awards:
            name = (a.supplier_name or "").strip()
            if not name:
                continue
            amt = _dec(a.awarded_amount) or _dec(a.total_line_amount) or Decimal("0")
            total_amount += amt
            slot = by_sup.setdefault(
                name,
                {
                    "rpe": a.supplier_rpe,
                    "count": 0,
                    "processes": set(),
                    "amount": Decimal("0"),
                    "last": None,
                    "currency": a.currency or "DOP",
                },
            )
            slot["count"] += 1
            slot["processes"].add(a.process_code)
            slot["amount"] += amt
            if a.award_date and (slot["last"] is None or a.award_date > slot["last"]):
                slot["last"] = a.award_date

        ranking: list[SupplierRankRow] = []
        for name, slot in by_sup.items():
            share = float(slot["amount"] / total_amount * 100) if total_amount > 0 else 0.0
            ranking.append(
                SupplierRankRow(
                    supplier_name=name,
                    supplier_rpe=slot["rpe"],
                    awards_count=slot["count"],
                    processes_count=len(slot["processes"]),
                    total_amount=slot["amount"],
                    currency=slot["currency"],
                    last_award_date=_iso(slot["last"]),
                    share_pct=round(share, 1),
                )
            )
        ranking.sort(key=lambda r: (r.total_amount, r.awards_count), reverse=True)

        if not ranking:
            return [], ConcentrationBlock(level="INSUFICIENTE", suppliers_count=0)

        top1 = ranking[0].share_pct
        top3 = sum(r.share_pct for r in ranking[:3])
        if top1 >= 50 or top3 >= 80:
            level = "ALTA"
        elif top1 >= 30 or top3 >= 60:
            level = "MEDIA"
        else:
            level = "BAJA"
        return ranking, ConcentrationBlock(
            level=level,  # type: ignore[arg-type]
            top1_share_pct=round(top1, 1),
            top3_share_pct=round(top3, 1),
            suppliers_count=len(ranking),
        )

    def _price_history(
        self, scored: list[tuple[DGCPHistoricalAward, float, list[str], str]]
    ) -> PriceHistoryBlock:
        points: list[PricePoint] = []
        units: list[float] = []
        caveats: list[str] = []
        for a, _, _, _ in sorted(
            scored,
            key=lambda x: x[0].award_date or datetime.min.replace(tzinfo=UTC),
        ):
            qty = _dec(a.quantity)
            unit = _dec(a.unit_price)
            if unit is None or qty is None or float(qty) <= 0 or float(unit) <= 0:
                continue
            units.append(float(unit))
            points.append(
                PricePoint(
                    award_date=_iso(a.award_date),
                    supplier_name=a.supplier_name,
                    quantity=qty,
                    unit_price=unit,
                    awarded_amount=_dec(a.awarded_amount) or _dec(a.total_line_amount),
                    process_code=a.process_code,
                    source_url=a.contract_url or a.process_url,
                )
            )
        if not points:
            return PriceHistoryBlock(
                available=False,
                caveats=["Sin precios unitarios con cantidad confiable en el conjunto analizado."],
            )
        last_u = units[-1]
        avg_u = mean(units)
        variation = ((last_u - avg_u) / avg_u * 100) if avg_u else None
        if len(points) < 3:
            caveats.append("Pocos puntos de precio; interpretar con cautela.")
        return PriceHistoryBlock(
            available=True,
            currency=scored[0][0].currency if scored else "DOP",
            points=points[-40:],
            last_unit_price=Decimal(str(round(last_u, 2))),
            avg_unit_price=Decimal(str(round(avg_u, 2))),
            min_unit_price=Decimal(str(round(min(units), 2))),
            max_unit_price=Decimal(str(round(max(units), 2))),
            median_unit_price=Decimal(str(round(median(units), 2))),
            variation_vs_last_pct=round(variation, 1) if variation is not None else None,
            caveats=caveats,
        )

    def _frequency(
        self, awards: list[DGCPHistoricalAward], window_months: int | None
    ) -> FrequencyBlock:
        dated = [a for a in awards if a.award_date]
        if not dated:
            return FrequencyBlock(available=False, summary="Sin fechas de adjudicación suficientes.")
        dates = sorted(a.award_date for a in dated if a.award_date)
        first, last = dates[0], dates[-1]
        processes = {a.process_code for a in dated}
        span_days = max(1, (last - first).days)
        months_span = max(1, round(span_days / 30))
        n_proc = max(len(processes), 1)
        if n_proc >= months_span:
            per_month = round(n_proc / months_span, 1)
            freq_phrase = f"unas {per_month} adjudicaciones/procesos por mes"
            approx = round(months_span / n_proc, 2)
        else:
            approx = round(months_span / n_proc, 1)
            freq_phrase = f"1 compra cada {approx} mes(es)"
        window_label = f"últimos {window_months} meses" if window_months else "el histórico disponible"
        summary = (
            f"Esta institución registra {len(processes)} procesos adjudicados "
            f"en {window_label} dentro del índice analizado. "
            f"Promedio aproximado: {freq_phrase}."
        )
        # Temporal pattern: months with most awards
        month_counts = Counter(d.month for d in dates)
        top_months = [m for m, _ in month_counts.most_common(3)]
        temporal = None
        if len(dates) >= 4 and month_counts.most_common(1)[0][1] >= 3:
            names = {
                1: "ene",
                2: "feb",
                3: "mar",
                4: "abr",
                5: "may",
                6: "jun",
                7: "jul",
                8: "ago",
                9: "sep",
                10: "oct",
                11: "nov",
                12: "dic",
            }
            top_n = month_counts.most_common(1)[0][1]
            temporal = (
                f"{top_n} de {len(dates)} adjudicaciones concentradas en "
                f"{', '.join(names[m] for m in top_months)} (evidencia descriptiva, no predicción)."
            )
        return FrequencyBlock(
            available=True,
            first_purchase_date=_iso(first),
            last_purchase_date=_iso(last),
            process_count=len(processes),
            purchase_count=len(dated),
            months_span=months_span,
            approx_months_between=approx,
            summary=summary,
            temporal_pattern=temporal,
        )

    def _modalities(self, awards: list[DGCPHistoricalAward]) -> list[ModalityStatsRow]:
        buckets: dict[str, dict[str, Any]] = {}
        for a in awards:
            key = (a.modality or "Sin modalidad").strip() or "Sin modalidad"
            slot = buckets.setdefault(
                key,
                {"processes": set(), "amount": Decimal("0"), "suppliers": set()},
            )
            slot["processes"].add(a.process_code)
            slot["amount"] += _dec(a.awarded_amount) or _dec(a.total_line_amount) or Decimal("0")
            if a.supplier_name:
                slot["suppliers"].add(a.supplier_name)
        rows = [
            ModalityStatsRow(
                modality=k,
                process_count=len(v["processes"]),
                total_amount=v["amount"],
                suppliers_count=len(v["suppliers"]),
            )
            for k, v in buckets.items()
        ]
        rows.sort(key=lambda r: r.total_amount, reverse=True)
        return rows

    def _product_lines(
        self,
        opp: DGCPOpportunity,
        scored: list[tuple[DGCPHistoricalAward, float, list[str], str]],
    ) -> list[ProductLineHistory]:
        info = opp.full_info or {}
        lines_raw: list[dict[str, Any]] = []
        matches = info.get("odoo_product_matches") or {}
        if isinstance(matches, dict) and matches.get("lines"):
            lines_raw = list(matches["lines"])
        elif isinstance(info.get("extracted_products"), list):
            lines_raw = list(info["extracted_products"])

        if not lines_raw:
            # Fallback: one synthetic line from title
            lines_raw = [{"line_number": 1, "description": opp.title, "original_text": opp.title}]

        out: list[ProductLineHistory] = []
        for i, ln in enumerate(lines_raw[:12], start=1):
            desc = (
                ln.get("original_text")
                or ln.get("description")
                or ln.get("descripcion")
                or opp.title
                or "—"
            )
            tokens = core_query_tokens(str(desc))
            best = None
            best_score = -1.0
            best_reasons: list[str] = []
            best_klass = "RELACIONADA"
            for award, score, reasons, klass in scored:
                blob = " ".join(
                    filter(
                        None,
                        [award.search_text, award.item_description, award.item_description_user],
                    )
                )
                s, r = score_award(
                    query_tokens=tokens,
                    query_institution=opp.institution or "",
                    query_objeto=opp.objeto_proceso,
                    award_institution=award.buyer_institution or "",
                    award_objeto=award.objeto_proceso,
                    award_search_text=blob,
                    same_institution_required=False,
                )
                if s > best_score:
                    best_score = s
                    best = award
                    best_reasons = r
                    best_klass = match_classification(
                        s, exact_item=self._exact_item_match(tokens, blob)
                    )
            row = self._to_row(best, best_score, best_reasons, best_klass) if best and best_score >= 20 else None
            out.append(
                ProductLineHistory(
                    line_number=int(ln.get("line_number") or i),
                    requested_description=str(desc)[:500],
                    last_purchase=row,
                    match_class=row.match_class if row else None,
                    similarity_pct=row.similarity_pct if row else None,
                )
            )
        return out

    def _budget_comparison(
        self, opp: DGCPOpportunity, last: LastPurchaseBlock
    ) -> BudgetComparisonBlock:
        est = _dec(opp.amount)
        last_amt = last.purchase.awarded_amount if last.purchase else None
        if not est or not last_amt or float(est) <= 0:
            return BudgetComparisonBlock(
                available=False,
                current_estimated_amount=est,
                current_currency=opp.currency or "DOP",
                caveats=["Se requiere presupuesto estimado del proceso y monto adjudicado comparable."],
            )
        variation = float((last_amt - est) / est * 100)
        caveats = [
            "El monto actual es ESTIMADO del proceso; el histórico es ADJUDICADO/CONTRATADO.",
            "Cantidad, especificación o alcance pueden no ser equivalentes.",
        ]
        return BudgetComparisonBlock(
            available=True,
            current_estimated_amount=est,
            current_currency=opp.currency or "DOP",
            last_comparable_amount=last_amt,
            variation_pct=round(variation, 1),
            caveats=caveats,
        )

    def _institution_profile(
        self,
        institution: str,
        awards: list[DGCPHistoricalAward],
        modalities: list[ModalityStatsRow],
    ) -> InstitutionProfileBlock:
        total = sum(
            (_dec(a.awarded_amount) or _dec(a.total_line_amount) or Decimal("0")) for a in awards
        )
        return InstitutionProfileBlock(
            institution=institution,
            known_award_lines=len(awards),
            known_processes=len({a.process_code for a in awards}),
            known_suppliers=len({a.supplier_name for a in awards if a.supplier_name}),
            total_awarded_amount=total,
            currency=(awards[0].currency if awards else "DOP") or "DOP",
            modalities=modalities,
        )

    def _quality_summary(self, rows: list[HistoricalPurchaseRow]) -> DataQualitySummary:
        c = Counter(r.data_quality for r in rows)
        if c["VERIFICADO"] >= max(1, len(rows) // 2):
            overall = "VERIFICADO"
        elif c["VERIFICADO"] + c["PARCIAL"] > 0:
            overall = "PARCIAL"
        else:
            overall = "INCOMPLETO"
        notes = []
        if c["INCOMPLETO"]:
            notes.append(f"{c['INCOMPLETO']} filas incompletas (faltan proveedor/monto/fecha/proceso).")
        notes.append("RNC de proveedor solo se muestra si viene en el payload fuente; el índice usa RPE.")
        return DataQualitySummary(
            overall=overall,  # type: ignore[arg-type]
            verified_count=c["VERIFICADO"],
            partial_count=c["PARCIAL"],
            incomplete_count=c["INCOMPLETO"],
            notes=notes,
        )

    def _executive_summary(
        self,
        opp: DGCPOpportunity,
        last: LastPurchaseBlock,
        ranking: list[SupplierRankRow],
        prices: PriceHistoryBlock,
        freq: FrequencyBlock,
        process_count: int,
        window_months: int | None,
    ) -> ExecutiveSummaryBlock:
        paras: list[str] = []
        window_label = f"últimos {window_months} meses" if window_months else "histórico disponible"
        paras.append(
            f"{opp.institution} registra {process_count} procesos adjudicados "
            f"comparables en el índice durante los {window_label}."
        )
        if last.available and last.purchase:
            p = last.purchase
            amt = f"{p.currency} {float(p.awarded_amount):,.2f}" if p.awarded_amount else "monto no disponible"
            date = (p.award_date or "")[:10]
            paras.append(
                f"La adquisición comparable más reciente "
                f"({last.match_class_label}) fue adjudicada a "
                f"{p.supplier_name or 'proveedor no identificado'} el {date} por {amt} "
                f"(proceso {p.process_code})."
            )
        if ranking:
            top = ranking[0]
            paras.append(
                f"El proveedor con mayor monto adjudicado en el conjunto analizado "
                f"({top.supplier_name}) representa {top.share_pct}%."
            )
        if prices.available and prices.min_unit_price is not None and prices.max_unit_price is not None:
            paras.append(
                f"El precio unitario observado para ítems comparables se encuentra entre "
                f"{prices.currency} {float(prices.min_unit_price):,.2f} y "
                f"{prices.currency} {float(prices.max_unit_price):,.2f}."
            )
        if freq.temporal_pattern:
            paras.append(freq.temporal_pattern)
        return ExecutiveSummaryBlock(paragraphs=paras, based_on_metrics_only=True)

    @staticmethod
    def _dedupe_by_process(rows: list[HistoricalPurchaseRow]) -> list[HistoricalPurchaseRow]:
        best: dict[str, HistoricalPurchaseRow] = {}
        for r in rows:
            prev = best.get(r.process_code)
            if not prev or (r.similarity_score or 0) > (prev.similarity_score or 0):
                best[r.process_code] = r
        return sorted(best.values(), key=lambda x: x.similarity_score or 0, reverse=True)
