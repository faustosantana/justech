"""Búsqueda histórica similar DGCP bajo demanda — sin indexación masiva."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from statistics import mean

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dgcp_bid_package import DGCPBidPackage
from app.models.dgcp_historical_award import DGCPHistoricalAward, DGCPHistoricalIndexJob
from app.models.dgcp_historical_similar_cache import DGCPProcessHistoricalSimilarResult
from app.models.dgcp_opportunity import DGCPOpportunity
from app.schemas.dgcp_historical import (
    DGCPHistoricalAwardItem,
    DGCPHistoricalIndexMeta,
    DGCPHistoricalIndicators,
    DGCPHistoricalPriceRecommendation,
    DGCPHistoricalSimilarResponse,
    DGCPHistoricalSimilarSearchRequest,
)
from app.services.dgcp_funnel import is_operational_interest_status
from app.services.dgcp_historical_similarity_engine import (
    SimilarityMatch,
    build_query_tokens,
    core_query_tokens,
    display_keywords,
    has_keyword_overlap,
    institution_matches_strict,
    normalize_text,
    score_award,
    score_similar_process,
    similarity_level,
    strict_core_tokens,
)
from app.services.dgcp_historical_index_service import (
    DEFAULT_INSTITUTION_INDEX_PAGES,
    DGCPHistoricalIndexService,
)
from app.services.price_intelligence_service import PriceIntelligenceService, PriceSearchFilters
from integrations.dgcp.client import DGCPClient
from integrations.dgcp.config import DGCPConfig
from integrations.dgcp.schemas import DGCPContratoArticuloRecord, DGCPContratoRecord

ELIGIBLE_STATUSES = {
    "interested",
    "preparing",
    "to_bid",
    "ready_to_submit",
    "submitted",
    "under_evaluation",
    "suspended",
    "awarded",
    "won",
    "lost",
}
CACHE_HOURS = 72
MAX_PAGES = 25
PAGE_SIZE = 50
MAX_CONSECUTIVE_EMPTY_PAGES = 5
LOCAL_SCAN_LIMIT = 4000
MIN_SCORE = 12
MIN_SCORE_OTHER_INSTITUTION = 55
MIN_SCORE_PROCESS_FAMILY = 35
DEFAULT_LIMIT = 10
DGCP_HTTP_TIMEOUT_SECONDS = 8.0
DGCP_LIVE_SEARCH_TIMEOUT_SECONDS = 18.0

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpportunitySnapshot:
    id: uuid.UUID
    code: str
    title: str
    institution: str
    description: str | None
    objeto_proceso: str | None
    currency: str | None
    full_info: dict
    raw_payload: dict


class DGCPHistoricalSimilarSearchService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.client = DGCPClient(
            DGCPConfig(
                base_url=settings.dgcp_api_base_url_resolved,
                api_key=settings.dgcp_api_key,
                timeout_seconds=DGCP_HTTP_TIMEOUT_SECONDS,
            )
        )

    async def get_cached(self, opportunity_id: uuid.UUID) -> DGCPHistoricalSimilarResponse:
        opp = await self._get_opportunity(opportunity_id)
        cache = await self._get_cache(opportunity_id)
        if cache and cache.expires_at > datetime.now(UTC):
            return self._response_from_cache(opp, cache, cached=True)
        return self._empty_response(
            opp,
            message="El histórico se cargará automáticamente al abrir el expediente.",
            cached=False,
        )

    async def search_bootstrap(
        self,
        opportunity_id: uuid.UUID,
        request: DGCPHistoricalSimilarSearchRequest | None = None,
    ) -> DGCPHistoricalSimilarResponse:
        """Búsqueda optimizada para bootstrap: índice local primero, API acotada."""
        request = request or DGCPHistoricalSimilarSearchRequest()
        opp = await self._get_opportunity(opportunity_id)
        self._ensure_eligible(opp)
        opp_snapshot = self._snapshot_opportunity(opp)
        keywords_list: list[str] = []
        index_meta = DGCPHistoricalIndexMeta()
        institution_code = self._institution_code(opp_snapshot)
        institution_name = opp_snapshot.institution or ""

        try:
            if not request.refresh:
                cache = await self._get_cache(opportunity_id)
                if cache and cache.expires_at > datetime.now(UTC) and cache.status != "error":
                    return self._response_from_cache(opp, cache, cached=True)

            keywords_list, query_tokens, core_tokens = await self._extract_keywords(
                opp, extra_query=request.extra_query
            )
            limit = request.limit or DEFAULT_LIMIT
            index_meta = await self._build_index_meta(institution_name, institution_code)

            if request.refresh or index_meta.institution_indexed == 0:
                try:
                    async with asyncio.timeout(DGCP_LIVE_SEARCH_TIMEOUT_SECONDS):
                        await self._ensure_institution_indexed(
                            institution_name,
                            institution_code,
                            refresh=request.refresh,
                            process_code=opp_snapshot.code,
                        )
                    await self.db.refresh(opp)
                    opp_snapshot = self._snapshot_opportunity(opp)
                    index_meta = await self._build_index_meta(institution_name, institution_code)
                except Exception as exc:
                    await self._safe_rollback()
                    index_meta = await self._build_index_meta(institution_name, institution_code)
                    status, message, error_message = self._external_failure_details(exc)
                    response = self._build_resilient_response(
                        opp_snapshot,
                        keywords_list=keywords_list,
                        source="local_index+dgcp_api_unavailable",
                        status=status,
                        message=message,
                        error_message=error_message,
                        index_meta=index_meta,
                    )
                    await self._persist_cache_safely(
                        opp=opp_snapshot,
                        keywords=keywords_list,
                        response=response,
                        pages_scanned=0,
                        candidates_scanned=0,
                        refresh=request.refresh,
                    )
                    return response

            local_matches = await self._search_local_index(
                opp_snapshot,
                institution_code=institution_code,
                query_tokens=query_tokens,
                core_tokens=core_tokens,
                limit=limit,
            )
            if len(local_matches) >= limit:
                return await self._finalize_bootstrap_response(
                    opp_snapshot,
                    local_matches[:limit],
                    keywords_list,
                    query_tokens,
                    core_tokens,
                    limit,
                    pages_scanned=0,
                    candidates_scanned=len(local_matches),
                    source="local_index",
                    refresh=request.refresh,
                    index_meta=index_meta,
                )

            page_limit = min(request.max_pages or 3, 3)
            request = DGCPHistoricalSimilarSearchRequest(
                refresh=request.refresh,
                limit=limit,
                max_pages=page_limit,
                extra_query=request.extra_query,
            )
            return await self.search(opportunity_id, request)
        except Exception as exc:
            await self._safe_rollback()
            response = self._build_resilient_response(
                opp_snapshot,
                keywords_list=keywords_list,
                source="local_index+fallback",
                status="error",
                message="No fue posible completar la búsqueda histórica; se devuelve un resultado vacío seguro.",
                error_message=f"{exc.__class__.__name__}: {exc}",
                index_meta=index_meta,
            )
            await self._persist_cache_safely(
                opp=opp_snapshot,
                keywords=keywords_list,
                response=response,
                pages_scanned=0,
                candidates_scanned=0,
                refresh=request.refresh,
            )
            return response

    async def _finalize_bootstrap_response(
        self,
        opp: DGCPOpportunity,
        unique_matches: list,
        keywords_list: list[str],
        query_tokens: set[str],
        core_tokens: set[str],
        limit: int,
        *,
        pages_scanned: int,
        candidates_scanned: int,
        source: str,
        refresh: bool,
        index_meta: DGCPHistoricalIndexMeta | None = None,
    ) -> DGCPHistoricalSimilarResponse:
        if index_meta is None:
            index_meta = await self._build_index_meta(opp.institution, self._institution_code(opp))
        query_unspsc = self._extract_unspsc(opp)
        other_matches = await self._search_other_institutions_local(
            opp,
            institution_code=self._institution_code(opp),
            query_tokens=query_tokens,
            core_tokens=core_tokens,
            limit=min(5, limit),
            query_unspsc=query_unspsc,
        )
        indicators = self._build_indicators(unique_matches)
        price_rec = await self._price_recommendation(unique_matches, opp)
        insights = self._ai_insights(unique_matches, indicators, price_rec, opp.institution, keywords_list)
        response = DGCPHistoricalSimilarResponse(
            opportunity_id=str(opp.id),
            process_code=opp.code,
            process_title=opp.title,
            buyer_institution=opp.institution,
            keywords_used=keywords_list,
            cached=False,
            searched_at=datetime.now(UTC).isoformat(),
            expires_at=(datetime.now(UTC) + timedelta(hours=CACHE_HOURS)).isoformat(),
            source=source,
            pages_scanned=pages_scanned,
            candidates_scanned=candidates_scanned,
            status="searched",
            message=f"Se encontraron {len(unique_matches)} compra(s) similar(es) para {opp.institution}.",
            matches=[self._match_to_item(m) for m in unique_matches],
            other_institution_matches=[self._match_to_item(m) for m in other_matches],
            total_matches=len(unique_matches),
            indicators=indicators,
            price_recommendation=price_rec,
            ai_insights=insights,
            index_meta=index_meta,
        )
        cache_error = await self._persist_cache_safely(
            opp=opp,
            keywords=keywords_list,
            response=response,
            pages_scanned=pages_scanned,
            candidates_scanned=candidates_scanned,
            refresh=refresh,
        )
        if cache_error:
            response.error_message = self._merge_error_messages(response.error_message, cache_error)
        return response

    async def search(
        self,
        opportunity_id: uuid.UUID,
        request: DGCPHistoricalSimilarSearchRequest | None = None,
    ) -> DGCPHistoricalSimilarResponse:
        request = request or DGCPHistoricalSimilarSearchRequest()
        opp = await self._get_opportunity(opportunity_id)
        self._ensure_eligible(opp)
        opp_snapshot = self._snapshot_opportunity(opp)
        keywords_list: list[str] = []
        index_meta = DGCPHistoricalIndexMeta()
        institution_code = self._institution_code(opp_snapshot)
        institution_name = opp_snapshot.institution or ""

        try:
            if not request.refresh:
                cache = await self._get_cache(opportunity_id)
                if cache and cache.expires_at > datetime.now(UTC) and cache.status != "error":
                    return self._response_from_cache(opp, cache, cached=True)

            keywords_list, query_tokens, core_tokens = await self._extract_keywords(
                opp, extra_query=request.extra_query
            )
            limit = request.limit or DEFAULT_LIMIT
            index_meta = await self._build_index_meta(institution_name, institution_code)

            external_status: str | None = None
            external_message: str | None = None
            error_message: str | None = None

            if request.refresh or index_meta.institution_indexed == 0:
                try:
                    async with asyncio.timeout(DGCP_LIVE_SEARCH_TIMEOUT_SECONDS):
                        await self._ensure_institution_indexed(
                            institution_name,
                            institution_code,
                            refresh=request.refresh,
                            process_code=opp_snapshot.code,
                        )
                    await self.db.refresh(opp)
                    opp_snapshot = self._snapshot_opportunity(opp)
                    index_meta = await self._build_index_meta(institution_name, institution_code)
                except Exception as exc:
                    await self._safe_rollback()
                    index_meta = await self._build_index_meta(institution_name, institution_code)
                    external_status, external_message, error_message = self._external_failure_details(exc)

            matches = await self._search_local_index(
                opp_snapshot,
                institution_code=institution_code,
                query_tokens=query_tokens,
                core_tokens=core_tokens,
                limit=limit,
            )
            pages_scanned = 0
            candidates_scanned = len(matches)
            source = "local_index"

            if len(matches) < limit and institution_code:
                try:
                    async with asyncio.timeout(DGCP_LIVE_SEARCH_TIMEOUT_SECONDS):
                        live_matches, live_pages, live_candidates = await self._search_live_institution(
                            opp_snapshot,
                            institution_code=institution_code,
                            query_tokens=query_tokens,
                            core_tokens=core_tokens,
                            limit=limit,
                        )
                    pages_scanned = live_pages
                    candidates_scanned += live_candidates
                    if live_matches:
                        source = "local_index+dgcp_api:unidad_compra"
                        seen = {f"{m.process_code}:{m.item_description}" for m in matches}
                        for m in live_matches:
                            key = f"{m.process_code}:{m.item_description}"
                            if key in seen:
                                continue
                            seen.add(key)
                            matches.append(m)
                            if len(matches) >= limit:
                                break
                except Exception as exc:
                    await self._safe_rollback()
                    ext_status, ext_message, ext_error = self._external_failure_details(exc)
                    external_status = external_status or ext_status
                    external_message = external_message or ext_message
                    error_message = self._merge_error_messages(error_message, ext_error)
                    source = "local_index+dgcp_api_unavailable"

            matches.sort(key=lambda m: (m.similarity_score, m.award_date or ""), reverse=True)
            unique_matches = matches[:limit]

            query_unspsc = self._extract_unspsc(opp_snapshot)
            other_matches = await self._search_other_institutions_local(
                opp_snapshot,
                institution_code=institution_code,
                query_tokens=query_tokens,
                core_tokens=core_tokens,
                limit=min(5, limit),
                query_unspsc=query_unspsc,
            )

            indicators = self._build_indicators(unique_matches)
            price_rec = await self._price_recommendation(unique_matches, opp_snapshot)
            insights = self._ai_insights(
                unique_matches, indicators, price_rec, opp_snapshot.institution, keywords_list
            )

            if not unique_matches and external_status:
                status = external_status
                message = external_message or "DGCP no estuvo disponible y no hay resultados locales."
            elif not unique_matches:
                status = "empty"
                if index_meta.institution_indexed == 0:
                    message = "No hay adjudicaciones indexadas para esta institución y la búsqueda devolvió un resultado vacío."
                else:
                    kw_sample = ", ".join(keywords_list[:6]) if keywords_list else "las palabras del proceso"
                    message = (
                        f"No encontramos compras relacionadas en {opp_snapshot.institution} con términos como {kw_sample}. "
                        f"Hay {index_meta.institution_indexed} adjudicación(es) indexada(s) de esta entidad."
                    )
            else:
                status = "searched"
                message = (
                    f"Se encontraron {len(unique_matches)} compra(s) relacionada(s) "
                    f"para {opp_snapshot.institution}."
                )

            response = DGCPHistoricalSimilarResponse(
                opportunity_id=str(opp_snapshot.id),
                process_code=opp_snapshot.code,
                process_title=opp_snapshot.title,
                buyer_institution=opp_snapshot.institution,
                keywords_used=keywords_list,
                cached=False,
                searched_at=datetime.now(UTC).isoformat(),
                expires_at=(datetime.now(UTC) + timedelta(hours=CACHE_HOURS)).isoformat(),
                source=source,
                pages_scanned=pages_scanned,
                candidates_scanned=candidates_scanned,
                status=status,
                message=message,
                error_message=error_message,
                matches=[self._match_to_item(m) for m in unique_matches],
                other_institution_matches=[self._match_to_item(m) for m in other_matches],
                total_matches=len(unique_matches),
                indicators=indicators,
                price_recommendation=price_rec,
                ai_insights=insights,
                index_meta=index_meta,
            )

            cache_error = await self._persist_cache_safely(
                opp=opp_snapshot,
                keywords=keywords_list,
                response=response,
                pages_scanned=pages_scanned,
                candidates_scanned=candidates_scanned,
                refresh=request.refresh,
            )
            if cache_error:
                response.error_message = self._merge_error_messages(response.error_message, cache_error)
            return response
        except Exception as exc:
            await self._safe_rollback()
            response = self._build_resilient_response(
                opp_snapshot,
                keywords_list=keywords_list,
                source="local_index+fallback",
                status="error",
                message="No fue posible completar la búsqueda histórica; se devuelve un resultado vacío seguro.",
                error_message=f"{exc.__class__.__name__}: {exc}",
                index_meta=index_meta,
            )
            await self._persist_cache_safely(
                opp=opp_snapshot,
                keywords=keywords_list,
                response=response,
                pages_scanned=0,
                candidates_scanned=0,
                refresh=request.refresh,
            )
            return response

    async def _search_live_institution(
        self,
        opp: DGCPOpportunity,
        *,
        institution_code: str | int,
        query_tokens: set[str],
        core_tokens: set[str],
        limit: int,
    ) -> tuple[list[SimilarityMatch], int, int]:
        """Consulta DGCP filtrando por unidad_compra e indexa en caliente."""
        indexer = DGCPHistoricalIndexService(self.db, self.tenant_id)
        stats = await indexer.index_for_institution(
            institution_code=institution_code,
            institution_name=opp.institution or "",
            max_pages=min(DEFAULT_INSTITUTION_INDEX_PAGES, 15),
            page_size=PAGE_SIZE,
        )
        await self.db.flush()
        local = await self._search_local_index(
            opp,
            institution_code=institution_code,
            query_tokens=query_tokens,
            core_tokens=core_tokens,
            limit=limit,
        )
        return local, stats.get("pages_indexed", 0), stats.get("items_indexed", 0)

    @staticmethod
    def _process_family(process_code: str | None) -> str | None:
        """Rubro/modalidad en códigos DGCP (p. ej. PEEX)."""
        if not process_code:
            return None
        parts = [p.lower() for p in process_code.split("-") if p]
        generic = {"daf", "ccc", "cd", "cm", "cp", "cc", "pepb", "lpn", "reside", "dgii"}
        for part in parts[1:]:
            if (len(part) == 4 and part.isdigit()) or part.isdigit():
                break
            if part not in generic and len(part) >= 3:
                return part
        return None

    async def _ensure_institution_indexed(
        self,
        institution_name: str,
        institution_code: str | int | None,
        *,
        refresh: bool,
        process_code: str | None = None,
    ) -> None:
        if not institution_code:
            return
        indexer = DGCPHistoricalIndexService(self.db, self.tenant_id)
        count = await indexer.count_institution_rows(institution_name, institution_code)
        family = self._process_family(process_code)
        try:
            if family and (count == 0 or refresh):
                family_count = await self._count_family_rows(
                    institution_name, institution_code, family
                )
                if family_count == 0:
                    await indexer.index_process_families(
                        institution_code=institution_code,
                        institution_name=institution_name,
                        families={family},
                        max_pages=12,
                    )
                    await self.db.flush()
            if count == 0:
                await indexer.index_for_institution(
                    institution_code=institution_code,
                    institution_name=institution_name,
                    max_pages=5,
                    page_size=PAGE_SIZE,
                )
                await self.db.flush()
        except Exception:
            await self._safe_rollback()
            raise

    async def _count_family_rows(
        self,
        institution_name: str,
        institution_code: str | int | None,
        family: str,
    ) -> int:
        family_norm = normalize_text(family)
        stmt = (
            select(DGCPHistoricalAward)
            .where(
                DGCPHistoricalAward.tenant_id == self.tenant_id,
                DGCPHistoricalAward.contract_url.isnot(None),
            )
            .limit(LOCAL_SCAN_LIMIT)
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        total = 0
        for row in rows:
            if family_norm not in normalize_text(row.process_code or ""):
                continue
            if institution_matches_strict(
                institution_name,
                row.buyer_institution,
                query_institution_code=institution_code,
                candidate_institution_code=row.buyer_institution_code,
            ):
                total += 1
        return total

    async def _build_index_meta(
        self,
        institution_name: str,
        institution_code: str | int | None,
    ) -> DGCPHistoricalIndexMeta:
        total = await self.db.scalar(
            select(func.count())
            .select_from(DGCPHistoricalAward)
            .where(
                DGCPHistoricalAward.tenant_id == self.tenant_id,
                DGCPHistoricalAward.contract_url.isnot(None),
            )
        )
        indexer = DGCPHistoricalIndexService(self.db, self.tenant_id)
        institution_count = await indexer.count_institution_rows(institution_name, institution_code)
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
        return DGCPHistoricalIndexMeta(
            total_indexed=int(total or 0),
            institution_indexed=institution_count,
            last_indexed_at=last_indexed.isoformat() if last_indexed else None,
            last_index_job_status=job.status if job else None,
        )

    @staticmethod
    def _institution_code(opp: DGCPOpportunity) -> str | int | None:
        for payload in (opp.full_info, opp.raw_payload):
            if not isinstance(payload, dict):
                continue
            code = payload.get("codigo_unidad_compra")
            if code is not None and str(code).strip():
                return code
        return None

    async def _extract_keywords(
        self,
        opp: DGCPOpportunity,
        *,
        extra_query: str | None,
    ) -> tuple[list[str], set[str], set[str]]:
        texts: list[str | None] = [opp.title, opp.description, opp.objeto_proceso, extra_query]
        for payload in (opp.full_info, opp.raw_payload):
            if not isinstance(payload, dict):
                continue
            for key in ("articulos", "artículos", "items", "lineas", "líneas", "detalle"):
                block = payload.get(key)
                if not block:
                    continue
                if isinstance(block, list):
                    for item in block:
                        if isinstance(item, dict):
                            texts.append(
                                item.get("descripcion")
                                or item.get("descripcion_articulo")
                                or item.get("descripcion_usuario")
                            )
                        elif isinstance(item, str):
                            texts.append(item)
                elif isinstance(block, str):
                    texts.append(block)

        pkg = await self._get_bid_package(opp.id)
        if pkg:
            reqs = pkg.requirements if isinstance(pkg.requirements, dict) else {}
            for item in reqs.get("technical") or []:
                if isinstance(item, dict):
                    texts.append(item.get("label"))
                    texts.append(item.get("matched_text"))

        tokens = build_query_tokens(*texts)
        core = core_query_tokens(*texts)
        keywords_list = display_keywords(core or tokens)
        return keywords_list, tokens, core

    async def _get_bid_package(self, opportunity_id: uuid.UUID) -> DGCPBidPackage | None:
        result = await self.db.execute(
            select(DGCPBidPackage).where(
                DGCPBidPackage.tenant_id == self.tenant_id,
                DGCPBidPackage.opportunity_id == opportunity_id,
            )
        )
        return result.scalar_one_or_none()

    async def _search_local_index(
        self,
        opp: DGCPOpportunity,
        *,
        institution_code: str | int | None,
        query_tokens: set[str],
        core_tokens: set[str],
        limit: int,
    ) -> list[SimilarityMatch]:
        stmt = (
            select(DGCPHistoricalAward)
            .where(
                DGCPHistoricalAward.tenant_id == self.tenant_id,
                DGCPHistoricalAward.contract_url.isnot(None),
            )
            .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
            .limit(LOCAL_SCAN_LIMIT)
        )
        if institution_code is not None:
            stmt = stmt.where(DGCPHistoricalAward.buyer_institution_code == str(institution_code))
        rows = list((await self.db.execute(stmt)).scalars().all())
        if not rows and institution_code is not None:
            stmt_all = (
                select(DGCPHistoricalAward)
                .where(
                    DGCPHistoricalAward.tenant_id == self.tenant_id,
                    DGCPHistoricalAward.contract_url.isnot(None),
                )
                .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
                .limit(LOCAL_SCAN_LIMIT)
            )
            all_rows = list((await self.db.execute(stmt_all)).scalars().all())
            rows = [
                row
                for row in all_rows
                if institution_matches_strict(
                    opp.institution,
                    row.buyer_institution,
                    query_institution_code=institution_code,
                    candidate_institution_code=row.buyer_institution_code,
                )
            ]
        matches: list[SimilarityMatch] = []
        filter_tokens = core_tokens or query_tokens

        for row in rows:
            if row.process_code == opp.code:
                continue
            if not institution_matches_strict(
                opp.institution,
                row.buyer_institution,
                query_institution_code=institution_code,
                candidate_institution_code=row.buyer_institution_code,
            ):
                continue

            process_family = self._process_family(opp.code)
            family_match = bool(
                process_family
                and process_family in normalize_text(row.process_code or "")
            )
            if filter_tokens and not has_keyword_overlap(filter_tokens, row.search_text) and not family_match:
                continue

            score, reasons = score_award(
                query_tokens=query_tokens,
                query_institution=opp.institution,
                query_objeto=opp.objeto_proceso,
                award_institution=row.buyer_institution,
                award_objeto=row.objeto_proceso or row.contract_object,
                award_search_text=row.search_text,
                same_institution_required=True,
            )
            if family_match:
                score += 30
                reasons.append(
                    f"Misma familia de procesos ({process_family.upper()}) en {opp.institution}"
                )
            min_score = MIN_SCORE_PROCESS_FAMILY if family_match else MIN_SCORE
            if score < min_score:
                continue
            matches.append(self._row_to_match(row, score, reasons))
            if len(matches) >= limit * 2:
                break

        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches[: limit * 2]

    async def _search_other_institutions_local(
        self,
        opp: DGCPOpportunity,
        *,
        institution_code: str | int | None,
        query_tokens: set[str],
        core_tokens: set[str],
        limit: int,
        query_unspsc: tuple[str | None, str | None, str | None] = (None, None, None),
    ) -> list[SimilarityMatch]:
        """Procesos similares en otras instituciones — scoring estricto por rubro técnico."""
        stmt = (
            select(DGCPHistoricalAward)
            .where(
                DGCPHistoricalAward.tenant_id == self.tenant_id,
                DGCPHistoricalAward.contract_url.isnot(None),
            )
            .order_by(DGCPHistoricalAward.award_date.desc().nullslast())
            .limit(LOCAL_SCAN_LIMIT)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        matches: list[SimilarityMatch] = []
        query_texts = [opp.title, opp.description or "", opp.objeto_proceso or ""]
        filter_tokens = strict_core_tokens(*query_texts)
        if not filter_tokens:
            return []

        seen_processes: set[str] = set()
        for row in rows:
            if row.process_code == opp.code:
                continue
            if institution_matches_strict(
                opp.institution,
                row.buyer_institution,
                query_institution_code=institution_code,
                candidate_institution_code=row.buyer_institution_code,
            ):
                continue

            candidate_texts = [
                row.item_description_user or row.item_description or "",
            ]
            candidate_unspsc = (row.unspsc_family, row.unspsc_class, row.unspsc_subclass)
            scored = score_similar_process(
                query_texts=query_texts,
                query_core=filter_tokens,
                query_objeto=opp.objeto_proceso,
                query_unspsc=query_unspsc,
                candidate_texts=candidate_texts,
                candidate_objeto=row.objeto_proceso or row.contract_object,
                candidate_unspsc=candidate_unspsc,
            )
            if not scored:
                continue
            score, reasons, matched_keywords = scored
            proc_key = row.process_code
            if proc_key in seen_processes:
                continue
            seen_processes.add(proc_key)
            matches.append(
                self._row_to_match(
                    row,
                    score,
                    reasons + ["Proceso comparable en otra institución"],
                    matched_keywords=matched_keywords,
                )
            )
            if len(matches) >= limit:
                break

        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches

    def _row_to_match(
        self,
        row: DGCPHistoricalAward,
        score: float,
        reasons: list[str],
        *,
        matched_keywords: list[str] | None = None,
    ) -> SimilarityMatch:
        raw = row.raw_payload if isinstance(row.raw_payload, dict) else {}
        proceso_meta = raw.get("proceso_meta") if isinstance(raw.get("proceso_meta"), dict) else {}
        pub_days = proceso_meta.get("publication_to_award_days")
        return SimilarityMatch(
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
            similarity_level=similarity_level(score),
            match_reasons=reasons,
            matched_keywords=matched_keywords or [],
            contract_object=row.contract_object,
            unit_measure=row.unit_measure,
            source=row.source or "dgcp_contratos_articulos",
            publication_to_award_days=int(pub_days) if pub_days is not None else None,
        )

    @staticmethod
    def _extract_unspsc(opp: DGCPOpportunity) -> tuple[str | None, str | None, str | None]:
        for payload in (opp.full_info, opp.raw_payload):
            if not isinstance(payload, dict):
                continue
            fam = payload.get("familia_unspsc") or payload.get("unspsc_family")
            cls = payload.get("clase_unspsc") or payload.get("unspsc_class")
            sub = payload.get("subclase_unspsc") or payload.get("unspsc_subclass")
            if fam or cls or sub:
                return (
                    str(fam) if fam else None,
                    str(cls) if cls else None,
                    str(sub) if sub else None,
                )
            for key in ("articulos", "artículos", "items"):
                block = payload.get(key)
                if not isinstance(block, list):
                    continue
                for item in block:
                    if not isinstance(item, dict):
                        continue
                    fam = item.get("familia_unspsc") or item.get("familia")
                    cls = item.get("clase_unspsc") or item.get("clase")
                    sub = item.get("subclase_unspsc") or item.get("subclase")
                    if fam or cls or sub:
                        return (
                            str(fam) if fam else None,
                            str(cls) if cls else None,
                            str(sub) if sub else None,
                        )
        return None, None, None

    @staticmethod
    def _build_search_text(contract: DGCPContratoRecord, item: DGCPContratoArticuloRecord) -> str:
        return normalize_text(
            " ".join(
                p
                for p in [
                    contract.descripcion,
                    item.descripcion_articulo,
                    item.descripcion_usuario,
                    contract.razon_social,
                ]
                if p
            )
        )

    async def get_institution_cache(
        self,
        institution: str | None,
        exclude_opportunity_id: uuid.UUID,
    ) -> DGCPHistoricalSimilarResponse | None:
        """Reutiliza caché reciente de otro proceso de la misma institución."""
        if not institution:
            return None
        result = await self.db.execute(
            select(DGCPProcessHistoricalSimilarResult)
            .where(
                DGCPProcessHistoricalSimilarResult.tenant_id == self.tenant_id,
                DGCPProcessHistoricalSimilarResult.buyer_institution == institution,
                DGCPProcessHistoricalSimilarResult.opportunity_id != exclude_opportunity_id,
                DGCPProcessHistoricalSimilarResult.expires_at > datetime.now(UTC),
                DGCPProcessHistoricalSimilarResult.status.notin_(("pending", "error")),
            )
            .order_by(DGCPProcessHistoricalSimilarResult.searched_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if not row:
            return None
        opp = await self._get_opportunity(exclude_opportunity_id)
        resp = self._response_from_cache(opp, row, cached=True)
        resp.message = (
            f"Resultado reutilizado de proceso similar en {institution} "
            f"(caché institución, {resp.total_matches} coincidencia(s))."
        )
        return resp

    async def _get_cache(self, opportunity_id: uuid.UUID) -> DGCPProcessHistoricalSimilarResult | None:
        result = await self.db.execute(
            select(DGCPProcessHistoricalSimilarResult).where(
                DGCPProcessHistoricalSimilarResult.tenant_id == self.tenant_id,
                DGCPProcessHistoricalSimilarResult.opportunity_id == opportunity_id,
            )
        )
        return result.scalar_one_or_none()

    async def _save_cache(
        self,
        *,
        opp: DGCPOpportunity,
        keywords: list[str],
        response: DGCPHistoricalSimilarResponse,
        pages_scanned: int,
        candidates_scanned: int,
        refresh: bool,
    ) -> None:
        existing = await self._get_cache(opp.id)
        expires_at = datetime.now(UTC) + timedelta(hours=CACHE_HOURS)
        payload = response.model_dump(mode="json")

        if existing:
            existing.keywords_used = keywords
            existing.searched_at = datetime.now(UTC)
            existing.expires_at = expires_at
            existing.results = payload
            existing.status = response.status
            existing.error_message = response.error_message
            existing.pages_scanned = pages_scanned
            existing.candidates_scanned = candidates_scanned
            existing.refresh_count = existing.refresh_count + (1 if refresh else 0)
            return

        self.db.add(
            DGCPProcessHistoricalSimilarResult(
                tenant_id=self.tenant_id,
                opportunity_id=opp.id,
                process_code=opp.code,
                buyer_institution=opp.institution,
                keywords_used=keywords,
                searched_at=datetime.now(UTC),
                expires_at=expires_at,
                results=payload,
                status=response.status,
                error_message=response.error_message,
                pages_scanned=pages_scanned,
                candidates_scanned=candidates_scanned,
                refresh_count=0,
            )
        )

    async def _persist_cache_safely(
        self,
        *,
        opp: DGCPOpportunity,
        keywords: list[str],
        response: DGCPHistoricalSimilarResponse,
        pages_scanned: int,
        candidates_scanned: int,
        refresh: bool,
    ) -> str | None:
        try:
            await self._save_cache(
                opp=opp,
                keywords=keywords,
                response=response,
                pages_scanned=pages_scanned,
                candidates_scanned=candidates_scanned,
                refresh=refresh,
            )
            await self.db.commit()
            return None
        except SQLAlchemyError as exc:
            await self._safe_rollback()
            logger.warning("Failed to persist DGCP historical similar cache: %s", exc)
            return f"cache_persist_failed: {exc.__class__.__name__}: {exc}"

    async def _safe_rollback(self) -> None:
        try:
            await self.db.rollback()
        except Exception:
            logger.exception("Failed to rollback DGCP historical similar transaction")

    @staticmethod
    def _merge_error_messages(current: str | None, extra: str | None) -> str | None:
        if not extra:
            return current
        if not current:
            return extra
        if extra in current:
            return current
        return f"{current} | {extra}"

    def _external_failure_details(self, exc: Exception) -> tuple[str, str, str]:
        if isinstance(exc, TimeoutError):
            return (
                "timeout",
                f"DGCP no respondió dentro del límite de {int(DGCP_LIVE_SEARCH_TIMEOUT_SECONDS)}s; se devuelve un resultado vacío o parcial con los datos locales disponibles.",
                f"timeout: {exc}",
            )
        if isinstance(exc, httpx.HTTPError):
            return (
                "network_error",
                "No fue posible consultar DGCP por un problema de red; se devuelve un resultado vacío o parcial con los datos locales disponibles.",
                f"{exc.__class__.__name__}: {exc}",
            )
        return (
            "external_error",
            "La consulta a DGCP no pudo completarse; se devuelve un resultado vacío o parcial con los datos locales disponibles.",
            f"{exc.__class__.__name__}: {exc}",
        )

    @staticmethod
    def _snapshot_opportunity(opp: DGCPOpportunity) -> OpportunitySnapshot:
        full_info = opp.full_info if isinstance(opp.full_info, dict) else {}
        raw_payload = opp.raw_payload if isinstance(opp.raw_payload, dict) else {}
        return OpportunitySnapshot(
            id=opp.id,
            code=opp.code,
            title=opp.title,
            institution=opp.institution,
            description=opp.description,
            objeto_proceso=opp.objeto_proceso,
            currency=opp.currency,
            full_info=dict(full_info),
            raw_payload=dict(raw_payload),
        )

    def _build_resilient_response(
        self,
        opp: DGCPOpportunity,
        *,
        keywords_list: list[str],
        source: str,
        status: str,
        message: str,
        error_message: str | None,
        index_meta: DGCPHistoricalIndexMeta | None = None,
    ) -> DGCPHistoricalSimilarResponse:
        return DGCPHistoricalSimilarResponse(
            opportunity_id=str(opp.id),
            process_code=opp.code,
            process_title=opp.title,
            buyer_institution=opp.institution,
            keywords_used=keywords_list,
            cached=False,
            searched_at=datetime.now(UTC).isoformat(),
            expires_at=(datetime.now(UTC) + timedelta(hours=CACHE_HOURS)).isoformat(),
            source=source,
            pages_scanned=0,
            candidates_scanned=0,
            status=status,
            message=message,
            error_message=error_message,
            matches=[],
            other_institution_matches=[],
            total_matches=0,
            indicators=DGCPHistoricalIndicators(),
            price_recommendation=None,
            ai_insights=[message],
            index_meta=index_meta or DGCPHistoricalIndexMeta(),
        )

    def _response_from_cache(
        self,
        opp: DGCPOpportunity,
        cache: DGCPProcessHistoricalSimilarResult,
        *,
        cached: bool,
    ) -> DGCPHistoricalSimilarResponse:
        data = cache.results or {}
        try:
            resp = DGCPHistoricalSimilarResponse.model_validate(data)
            resp.cached = cached
            resp.searched_at = cache.searched_at.isoformat()
            resp.expires_at = cache.expires_at.isoformat()
            resp.pages_scanned = cache.pages_scanned
            resp.candidates_scanned = cache.candidates_scanned
            return resp
        except Exception:
            return self._empty_response(opp, message="Cache inválido — ejecute una nueva búsqueda.", cached=False)

    def _empty_response(
        self,
        opp: DGCPOpportunity,
        *,
        message: str,
        cached: bool,
    ) -> DGCPHistoricalSimilarResponse:
        return DGCPHistoricalSimilarResponse(
            opportunity_id=str(opp.id),
            process_code=opp.code,
            process_title=opp.title,
            buyer_institution=opp.institution,
            keywords_used=[],
            cached=cached,
            searched_at=None,
            expires_at=None,
            source="dgcp_api_on_demand",
            status="pending",
            message=message,
            matches=[],
            total_matches=0,
        )

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
    def _ensure_eligible(opp: DGCPOpportunity) -> None:
        if not is_operational_interest_status(opp.status):
            raise ValueError(
                "La búsqueda histórica está disponible cuando el proceso tiene interés operativo "
                "(interesada, en preparación, presentada, etc.)."
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
            competition_level="alta" if len(supplier_counts) >= 3 else "media" if len(supplier_counts) >= 2 else "baja",
        )

    async def _price_recommendation(
        self,
        matches: list[SimilarityMatch],
        opp: DGCPOpportunity,
    ) -> DGCPHistoricalPriceRecommendation | None:
        prices = [float(m.unit_price) for m in matches if m.unit_price and float(m.unit_price) > 0]
        if not prices:
            return None
        avg_p = mean(prices)
        min_p = min(prices)
        max_p = max(prices)
        offer_low = round(avg_p * 0.93, 2)
        offer_high = round(avg_p * 1.07, 2)
        return DGCPHistoricalPriceRecommendation(
            currency=opp.currency or "DOP",
            historical_min_unit=Decimal(str(round(min_p, 2))),
            historical_avg_unit=Decimal(str(round(avg_p, 2))),
            historical_max_unit=Decimal(str(round(max_p, 2))),
            recommended_offer_low=Decimal(str(offer_low)),
            recommended_offer_high=Decimal(str(offer_high)),
            summary=(
                f"Recomendación: ofertar entre {opp.currency} {offer_low:,.2f} y {offer_high:,.2f} por unidad "
                f"(promedio histórico: {opp.currency} {avg_p:,.2f})."
            ),
        )

    def _ai_insights(
        self,
        matches: list[SimilarityMatch],
        indicators: DGCPHistoricalIndicators,
        price_rec: DGCPHistoricalPriceRecommendation | None,
        institution: str,
        keywords: list[str],
    ) -> list[str]:
        if not matches:
            kw = ", ".join(keywords[:6]) if keywords else "los términos del proceso"
            return [
                f"No encontramos compras similares recientes en {institution} usando {kw}.",
                "Intente actualizar la búsqueda tras analizar los ítems del proceso o agregue palabras clave.",
            ]
        insights: list[str] = []
        dates = [m.award_date[:10] for m in matches if m.award_date]
        if dates:
            insights.append(
                f"Esta entidad compró productos similares en: {', '.join(dates[:3])}."
            )
        if indicators.most_frequent_supplier:
            insights.append(
                f"El proveedor que más aparece es «{indicators.most_frequent_supplier}» "
                f"({indicators.most_frequent_supplier_wins} adjudicación/es)."
            )
        if indicators.avg_unit_price:
            insights.append(f"El precio histórico promedio fue RD${indicators.avg_unit_price:,.2f}.")
        if price_rec:
            insights.append(price_rec.summary)
        return insights

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
            contract_object=m.contract_object,
            unit_measure=m.unit_measure,
            unit_price=m.unit_price,
            quantity=m.quantity,
            awarded_amount=m.awarded_amount,
            modality=m.modality,
            contract_url=m.contract_url,
            process_url=m.process_url,
            source=m.source,
            publication_to_award_days=m.publication_to_award_days,
            similarity_score=m.similarity_score,
            similarity_level=m.similarity_level,
            match_reasons=m.match_reasons,
            matched_keywords=m.matched_keywords or [],
        )
