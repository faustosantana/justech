"""Búsqueda inteligente de histórico de adjudicaciones y recomendaciones de precio."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dgcp_historical_award import DGCPHistoricalAward, DGCPHistoricalIndexJob
from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.dgcp_historical import (
    DGCPHistoricalAwardItem,
    DGCPHistoricalAwardsResponse,
    DGCPHistoricalIndexResponse,
    DGCPHistoricalIndicators,
    DGCPHistoricalPriceRecommendation,
    DGCPHistoricalSearchFilters,
)
from app.services.dgcp_historical_index_service import DGCPHistoricalIndexService
from app.services.dgcp_historical_job_status import (
    JOB_RUNNING,
    JOB_SOURCE_UNAVAILABLE,
    JOB_SUCCESS,
    classify_exception,
    mark_job_complete,
)
from app.services.dgcp_historical_similarity_engine import (
    SimilarityMatch,
    build_query_tokens,
    score_award,
    similarity_level,
)
from app.services.price_intelligence_service import PriceIntelligenceService, PriceSearchFilters


class DGCPHistoricalAwardsService:
    SCAN_LIMIT = 8000

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, *, user_id: uuid.UUID | None = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def get_index_stats(
        self,
        *,
        institution_name: str | None = None,
        institution_code: str | int | None = None,
    ) -> dict:
        total = await self.db.scalar(
            select(func.count()).select_from(DGCPHistoricalAward).where(
                DGCPHistoricalAward.tenant_id == self.tenant_id,
                DGCPHistoricalAward.contract_url.isnot(None),
            )
        )
        institution_count = 0
        if institution_name:
            institution_count = await DGCPHistoricalIndexService(self.db, self.tenant_id).count_institution_rows(
                institution_name,
                institution_code,
            )
        last_indexed = await self.db.scalar(
            select(func.max(DGCPHistoricalAward.indexed_at)).where(
                DGCPHistoricalAward.tenant_id == self.tenant_id
            )
        )
        last_job = await self.db.execute(
            select(DGCPHistoricalIndexJob)
            .where(DGCPHistoricalIndexJob.tenant_id == self.tenant_id)
            .order_by(DGCPHistoricalIndexJob.started_at.desc())
            .limit(1)
        )
        job = last_job.scalar_one_or_none()
        return {
            "total_indexed": int(total or 0),
            "institution_indexed": institution_count,
            "institution_name": institution_name,
            "institution_code": str(institution_code) if institution_code is not None else None,
            "last_indexed_at": last_indexed.isoformat() if last_indexed else None,
            "last_index_job_status": job.status if job else None,
            "data_available": bool(total),
            "source": "dgcp_api:contratos,contratos/articulos",
        }

    async def run_index(
        self,
        *,
        max_pages: int = 10,
        page_size: int = 100,
        institution_code: str | int | None = None,
        institution_name: str | None = None,
    ) -> DGCPHistoricalIndexResponse:
        indexer = DGCPHistoricalIndexService(self.db, self.tenant_id)
            job = DGCPHistoricalIndexJob(
                tenant_id=self.tenant_id,
                status=JOB_RUNNING,
            )
            self.db.add(job)
            await self.db.flush()
            try:
                stats = await indexer.index_for_institution(
                    institution_code=institution_code,
                    institution_name=institution_name,
                    max_pages=max_pages,
                    page_size=page_size,
                )
                job.pages_indexed = stats.get("pages_indexed", 0)
                job.contracts_indexed = stats.get("contracts_indexed", 0)
                job.items_indexed = stats.get("items_indexed", 0)
                mark_job_complete(job, status=JOB_SUCCESS, source_status="AVAILABLE")
            except Exception as exc:
                status = classify_exception(exc)
                mark_job_complete(
                    job,
                    status=status,
                    error_message=str(exc)[:2000],
                    source_status="UNAVAILABLE" if status == JOB_SOURCE_UNAVAILABLE else None,
                )
            await self.db.flush()
            await self.db.refresh(job)
        else:
            job = await indexer.run_index(max_pages=max_pages, page_size=page_size)
        await self.db.commit()
        ok = job.status in (JOB_SUCCESS, "completed", "success")
        return DGCPHistoricalIndexResponse(
            job_id=job.id,
            status=job.status,
            pages_indexed=job.pages_indexed,
            contracts_indexed=job.contracts_indexed,
            items_indexed=job.items_indexed,
            error_message=job.error_message,
            message=(
                f"Indexados {job.items_indexed} ítems adjudicados"
                if ok
                else job.error_message or "Indexación fallida"
            ),
        )

    async def search_for_opportunity(
        self,
        opportunity_id: uuid.UUID,
        filters: DGCPHistoricalSearchFilters | None = None,
        *,
        query: str | None = None,
    ) -> DGCPHistoricalAwardsResponse:
        opp = await self._get_opportunity(opportunity_id)
        filters = filters or DGCPHistoricalSearchFilters()
        return await self._search(
            title=query or opp.title,
            description=query or opp.description,
            institution=opp.institution,
            objeto_proceso=opp.objeto_proceso,
            current_amount=opp.amount,
            current_currency=opp.currency,
            process_code=opp.code,
            process_url=opp.source_url,
            filters=filters,
        )

    async def search_free(
        self,
        *,
        query: str,
        institution: str | None = None,
        filters: DGCPHistoricalSearchFilters | None = None,
    ) -> DGCPHistoricalAwardsResponse:
        filters = filters or DGCPHistoricalSearchFilters()
        return await self._search(
            title=query,
            description=query,
            institution=institution or "",
            objeto_proceso=None,
            current_amount=None,
            current_currency="DOP",
            process_code=None,
            process_url=None,
            filters=filters,
        )

    async def list_awards(self, *, limit: int = 50, offset: int = 0) -> list[DGCPHistoricalAwardItem]:
        result = await self.db.execute(
            select(DGCPHistoricalAward)
            .where(DGCPHistoricalAward.tenant_id == self.tenant_id)
            .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
            .offset(offset)
            .limit(limit)
        )
        return [self._to_item(row, score=0, level="—", reasons=[]) for row in result.scalars().all()]

    async def _search(
        self,
        *,
        title: str,
        description: str | None,
        institution: str,
        objeto_proceso: str | None,
        current_amount: Decimal | None,
        current_currency: str,
        process_code: str | None,
        process_url: str | None,
        filters: DGCPHistoricalSearchFilters,
    ) -> DGCPHistoricalAwardsResponse:
        stats = await self.get_index_stats()
        if not stats["data_available"]:
            return DGCPHistoricalAwardsResponse(
                process_code=process_code,
                process_title=title,
                data_available=False,
                message=(
                    "No hay histórico indexado todavía. Ejecute «Indexar histórico DGCP» "
                    "desde Configuración o POST /api/v1/dgcp/historical-awards/index"
                ),
                missing_sources=["dgcp_contratos_articulos_index"],
                matches=[],
                indicators=DGCPHistoricalIndicators(),
                price_recommendation=None,
                ai_insights=[
                    "Sin datos históricos locales. La API DGCP expone /contratos y /contratos/articulos — indexe al menos 10 páginas para comenzar.",
                ],
            )

        query_tokens = build_query_tokens(title, description, objeto_proceso)
        stmt = select(DGCPHistoricalAward).where(DGCPHistoricalAward.tenant_id == self.tenant_id)

        if filters.same_institution_only and institution:
            stmt = stmt.where(DGCPHistoricalAward.buyer_institution.ilike(f"%{institution[:40]}%"))

        if filters.years_back:
            cutoff = datetime.now(UTC) - timedelta(days=365 * filters.years_back)
            stmt = stmt.where(DGCPHistoricalAward.award_date >= cutoff)

        if filters.supplier_name:
            stmt = stmt.where(DGCPHistoricalAward.supplier_name.ilike(f"%{filters.supplier_name}%"))

        stmt = stmt.order_by(DGCPHistoricalAward.award_date.desc().nullslast()).limit(self.SCAN_LIMIT)
        rows = list((await self.db.execute(stmt)).scalars().all())

        matches: list[SimilarityMatch] = []
        for row in rows:
            if process_code and row.process_code == process_code:
                continue
            score, reasons = score_award(
                query_tokens=query_tokens,
                query_institution=institution,
                query_objeto=objeto_proceso,
                award_institution=row.buyer_institution,
                award_objeto=row.objeto_proceso,
                award_search_text=row.search_text,
                same_institution_required=filters.same_institution_only,
            )
            if filters.min_similarity and score < filters.min_similarity:
                continue
            if score < 12 and not filters.same_institution_only:
                continue
            level = similarity_level(score)
            if filters.same_product_only and level == "muy_baja":
                continue
            matches.append(
                SimilarityMatch(
                    award_id=str(row.id),
                    process_code=row.process_code,
                    contract_code=row.contract_code,
                    buyer_institution=row.buyer_institution,
                    supplier_name=row.supplier_name,
                    award_date=row.award_date.isoformat() if row.award_date else None,
                    item_description=row.item_description_user or row.item_description,
                    unit_price=row.unit_price,
                    quantity=row.quantity,
                    awarded_amount=row.awarded_amount or row.total_line_amount,
                    modality=row.modality,
                    contract_url=row.contract_url,
                    process_url=row.process_url,
                    similarity_score=round(score, 1),
                    similarity_level=level,
                    match_reasons=reasons,
                )
            )

        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        top = matches[: filters.limit or 25]

        indicators = self._build_indicators(top)
        price_rec = await self._price_recommendation(
            top, current_amount=current_amount, currency=current_currency, title=title
        )
        insights = self._ai_insights(top, indicators, price_rec, institution)

        return DGCPHistoricalAwardsResponse(
            process_code=process_code,
            process_title=title,
            process_url=process_url,
            data_available=True,
            message=(
                f"Se encontraron {len(top)} adjudicación(es) similar(es)"
                if top
                else "No se encontraron coincidencias suficientes. Amplíe el índice histórico o relaje filtros."
            ),
            matches=[self._match_to_item(m) for m in top],
            indicators=indicators,
            price_recommendation=price_rec,
            ai_insights=insights,
            filters_applied=filters.model_dump(),
            total_candidates_scanned=len(rows),
        )

    def _build_indicators(self, matches: list[SimilarityMatch]) -> DGCPHistoricalIndicators:
        prices = [float(m.unit_price) for m in matches if m.unit_price and float(m.unit_price) > 0]
        suppliers = [m.supplier_name for m in matches if m.supplier_name]
        supplier_counts = Counter(suppliers)
        top_supplier, top_count = supplier_counts.most_common(1)[0] if supplier_counts else (None, 0)

        return DGCPHistoricalIndicators(
            similar_process_count=len({m.process_code for m in matches}),
            similar_item_count=len(matches),
            min_unit_price=Decimal(str(min(prices))) if prices else None,
            avg_unit_price=Decimal(str(round(mean(prices), 2))) if prices else None,
            max_unit_price=Decimal(str(max(prices))) if prices else None,
            last_awarded_unit_price=Decimal(str(prices[0])) if prices else None,
            most_frequent_supplier=top_supplier,
            most_frequent_supplier_wins=top_count,
            competition_level="alta" if len(supplier_counts) >= 4 else "media" if len(supplier_counts) >= 2 else "baja",
        )

    async def _price_recommendation(
        self,
        matches: list[SimilarityMatch],
        *,
        current_amount: Decimal | None,
        currency: str,
        title: str,
    ) -> DGCPHistoricalPriceRecommendation | None:
        prices = [float(m.unit_price) for m in matches if m.unit_price and float(m.unit_price) > 0]
        if not prices:
            return None

        avg_p = mean(prices)
        min_p = min(prices)
        max_p = max(prices)
        offer_low = round(avg_p * 0.93, 2)
        offer_high = round(avg_p * 1.07, 2)

        market_prices: list[float] = []
        try:
            pi = PriceIntelligenceService(self.db, self.tenant_id)
            for token in title.split()[:3]:
                if len(token) < 4:
                    continue
                res = await pi.search(PriceSearchFilters(q=token, limit=5))
                for p in res.items:
                    if p.cost_price:
                        market_prices.append(float(p.cost_price))
        except Exception:
            pass

        market_avg = mean(market_prices) if market_prices else None
        margin_risk = None
        if market_avg and offer_low < market_avg * 0.85:
            margin_risk = "Riesgo de margen bajo si el costo de proveedor supera el precio histórico adjudicado."
        if current_amount and float(current_amount) > 0 and avg_p > 0:
            est_qty = max(float(m.quantity or 1) for m in matches) if matches else 1
            current_unit = float(current_amount) / est_qty
            if current_unit > max_p * 1.15:
                margin_risk = (margin_risk or "") + " Precio estimado actual por encima del histórico máximo."

        return DGCPHistoricalPriceRecommendation(
            currency=currency,
            historical_min_unit=Decimal(str(round(min_p, 2))),
            historical_avg_unit=Decimal(str(round(avg_p, 2))),
            historical_max_unit=Decimal(str(round(max_p, 2))),
            recommended_offer_low=Decimal(str(offer_low)),
            recommended_offer_high=Decimal(str(offer_high)),
            market_supplier_avg=Decimal(str(round(market_avg, 2))) if market_avg else None,
            margin_risk=margin_risk,
            summary=(
                f"Ofertar entre {currency} {offer_low:,.2f} y {offer_high:,.2f} por unidad "
                f"(promedio histórico adjudicado: {currency} {avg_p:,.2f})."
            ),
        )

    def _ai_insights(
        self,
        matches: list[SimilarityMatch],
        indicators: DGCPHistoricalIndicators,
        price_rec: DGCPHistoricalPriceRecommendation | None,
        institution: str,
    ) -> list[str]:
        insights: list[str] = []
        if not matches:
            insights.append("No hay adjudicaciones históricas similares indexadas para esta consulta.")
            return insights

        if indicators.most_frequent_supplier:
            insights.append(
                f"El proveedor «{indicators.most_frequent_supplier}» ganó "
                f"{indicators.most_frequent_supplier_wins} proceso(s) similar(es)."
            )
        if indicators.avg_unit_price:
            insights.append(
                f"El precio unitario histórico promedio es RD${indicators.avg_unit_price:,.2f}."
            )
        if price_rec:
            insights.append(price_rec.summary)
        if len(matches) >= 3:
            insights.append(f"La institución «{institution}» compra con frecuencia este rubro ({len(matches)} coincidencias).")
        if indicators.competition_level == "alta":
            insights.append("Nivel de competencia histórico alto — varios proveedores distintos adjudicados.")
        if price_rec and price_rec.margin_risk:
            insights.append(price_rec.margin_risk)
        return insights

    async def _get_opportunity(self, opportunity_id: uuid.UUID) -> DGCPOpportunity:
        result = await self.db.execute(
            select(DGCPOpportunity).where(
                DGCPOpportunity.id == opportunity_id,
                DGCPOpportunity.tenant_id == self.tenant_id,
            )
        )
        opp = result.scalar_one_or_none()
        if not opp:
            raise ValueError("Licitación no encontrada")
        return opp

    @staticmethod
    def _match_to_item(m: SimilarityMatch) -> DGCPHistoricalAwardItem:
        return DGCPHistoricalAwardItem(
            id=m.award_id,
            process_code=m.process_code,
            contract_code=m.contract_code,
            buyer_institution=m.buyer_institution,
            supplier_name=m.supplier_name,
            award_date=m.award_date,
            item_description=m.item_description,
            unit_price=m.unit_price,
            quantity=m.quantity,
            awarded_amount=m.awarded_amount,
            modality=m.modality,
            contract_url=m.contract_url,
            process_url=m.process_url,
            similarity_score=m.similarity_score,
            similarity_level=m.similarity_level,
            match_reasons=m.match_reasons,
        )

    @staticmethod
    def _to_item(row: DGCPHistoricalAward, *, score: float, level: str, reasons: list[str]) -> DGCPHistoricalAwardItem:
        return DGCPHistoricalAwardItem(
            id=str(row.id),
            process_code=row.process_code,
            contract_code=row.contract_code,
            buyer_institution=row.buyer_institution,
            supplier_name=row.supplier_name,
            award_date=row.award_date.isoformat() if row.award_date else None,
            item_description=row.item_description_user or row.item_description,
            unit_price=row.unit_price,
            quantity=row.quantity,
            awarded_amount=row.awarded_amount or row.total_line_amount,
            modality=row.modality,
            contract_url=row.contract_url,
            process_url=row.process_url,
            similarity_score=score,
            similarity_level=level,
            match_reasons=reasons,
        )
