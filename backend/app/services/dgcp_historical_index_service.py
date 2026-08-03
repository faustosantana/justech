"""Indexación de adjudicaciones históricas desde API DGCP (/contratos, /contratos/articulos)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.dgcp_historical_award import DGCPHistoricalAward, DGCPHistoricalIndexJob
from app.models.dgcp_opportunity import DGCPOpportunity
from app.services.dgcp_historical_similarity_engine import institution_matches_strict, normalize_text
from integrations.dgcp.client import DGCPClient
from integrations.dgcp.config import DGCPConfig
from integrations.dgcp.schemas import DGCPContratoArticuloRecord, DGCPContratoRecord, DGCPProcesoRecord

DEFAULT_INSTITUTION_INDEX_PAGES = 60
DGCP_HTTP_TIMEOUT_SECONDS = 8.0


class DGCPHistoricalIndexService:
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
        self._contracts_cache: dict[str, DGCPContratoRecord] = {}
        self._proceso_meta_cache: dict[str, dict] = {}

    async def run_index(
        self,
        *,
        max_pages: int = 10,
        page_size: int = 100,
        trigger: str = "manual",
    ) -> DGCPHistoricalIndexJob:
        job = DGCPHistoricalIndexJob(tenant_id=self.tenant_id, status="running")
        self.db.add(job)
        await self.db.flush()

        try:
            for page in range(1, max_pages + 1):
                contracts_resp = await self.client.fetch_contratos(page=page, limit=page_size)
                for c in contracts_resp.content:
                    if isinstance(c, DGCPContratoRecord):
                        self._contracts_cache[f"{c.codigo_proceso}:{c.codigo_contrato}"] = c
                        job.contracts_indexed += 1

                response = await self.client.fetch_contratos_articulos(page=page, limit=page_size)
                job.pages_indexed = page
                for item in response.content:
                    if isinstance(item, DGCPContratoArticuloRecord):
                        created = await self._upsert_articulo(item)
                        if created:
                            job.items_indexed += 1
                if page >= response.pages:
                    break
            job.status = "completed"
            job.completed_at = datetime.now(UTC)
        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def index_for_institution(
        self,
        *,
        institution_code: int | str,
        institution_name: str,
        max_pages: int = DEFAULT_INSTITUTION_INDEX_PAGES,
        page_size: int = 100,
    ) -> dict[str, int]:
        """Indexa adjudicaciones filtradas por código de unidad de compra DGCP."""
        contracts_indexed = 0
        items_indexed = 0
        pages_indexed = 0
        seen_processes: set[str] = set()

        for page in range(1, max_pages + 1):
            contracts_resp = await self.client.fetch_contratos(
                page=page,
                limit=page_size,
                unidad_compra=institution_code,
            )
            pages_indexed = page
            page_processes: set[str] = set()

            for contract in contracts_resp.content:
                if not isinstance(contract, DGCPContratoRecord):
                    continue
                if not institution_matches_strict(
                    institution_name,
                    contract.unidad_compra,
                    query_institution_code=institution_code,
                    candidate_institution_code=contract.codigo_unidad_compra,
                ):
                    continue
                self._contracts_cache[f"{contract.codigo_proceso}:{contract.codigo_contrato}"] = contract
                contracts_indexed += 1
                page_processes.add(contract.codigo_proceso)

            for process_code in page_processes:
                if process_code in seen_processes:
                    continue
                seen_processes.add(process_code)
                items_indexed += await self._index_process_items(process_code)

            if page >= contracts_resp.pages or not contracts_resp.content:
                break

        return {
            "pages_indexed": pages_indexed,
            "contracts_indexed": contracts_indexed,
            "items_indexed": items_indexed,
        }

    async def index_process_families(
        self,
        *,
        institution_code: int | str,
        institution_name: str,
        families: set[str],
        max_pages: int = 20,
        page_size: int = 100,
    ) -> dict[str, int]:
        """Indexa procesos de la institución cuyo código contiene familias/rubros (p. ej. PEEX)."""
        if not families:
            return {"pages_indexed": 0, "contracts_indexed": 0, "items_indexed": 0}

        families_norm = {normalize_text(f) for f in families if f}
        seen_processes: set[str] = set()
        items_indexed = 0
        contracts_indexed = 0
        pages_indexed = 0

        for page in range(1, max_pages + 1):
            contracts_resp = await self.client.fetch_contratos(
                page=page,
                limit=page_size,
                unidad_compra=institution_code,
            )
            pages_indexed = page
            for contract in contracts_resp.content:
                if not isinstance(contract, DGCPContratoRecord):
                    continue
                pcode = contract.codigo_proceso or ""
                if not any(f in normalize_text(pcode) for f in families_norm):
                    continue
                if not institution_matches_strict(
                    institution_name,
                    contract.unidad_compra,
                    query_institution_code=institution_code,
                    candidate_institution_code=contract.codigo_unidad_compra,
                ):
                    continue
                self._contracts_cache[f"{pcode}:{contract.codigo_contrato}"] = contract
                contracts_indexed += 1
                if pcode in seen_processes:
                    continue
                seen_processes.add(pcode)
                items_indexed += await self._index_process_items(pcode)

            if page >= contracts_resp.pages or not contracts_resp.content:
                break

        return {
            "pages_indexed": pages_indexed,
            "contracts_indexed": contracts_indexed,
            "items_indexed": items_indexed,
        }

    async def _index_process_items(self, process_code: str) -> int:
        indexed = 0
        page = 1
        while True:
            response = await self.client.fetch_contratos_articulos(
                page=page,
                limit=200,
                proceso=process_code,
            )
            if not response.content:
                break
            for item in response.content:
                if isinstance(item, DGCPContratoArticuloRecord):
                    contract = await self._ensure_contract(item.codigo_proceso, item.codigo_contrato)
                    if contract and await self._upsert_articulo(item):
                        indexed += 1
            if page >= response.pages:
                break
            page += 1
        return indexed

    async def _ensure_contract(self, process_code: str, contract_code: str) -> DGCPContratoRecord | None:
        key = f"{process_code}:{contract_code}"
        cached = self._contracts_cache.get(key)
        if cached:
            return cached
        response = await self.client.fetch_contratos(page=1, limit=5, proceso=process_code, contrato=contract_code)
        for contract in response.content:
            if isinstance(contract, DGCPContratoRecord):
                self._contracts_cache[key] = contract
                return contract
        return None

    async def _upsert_articulo(self, item: DGCPContratoArticuloRecord) -> bool:
        contract = await self._get_contract(item.codigo_proceso, item.codigo_contrato)
        if not contract or not contract.url_contrato:
            return False

        proceso_meta = await self._proceso_meta(item.codigo_proceso)
        award_date = contract.fecha_adjudicacion or item.fecha_creacion_contrato
        publication_date = proceso_meta.get("publication_date")
        publication_to_award_days: int | None = None
        if publication_date and award_date:
            pub = publication_date if isinstance(publication_date, datetime) else None
            awd = award_date if isinstance(award_date, datetime) else None
            if pub and awd:
                publication_to_award_days = max(0, (awd - pub).days)

        item_desc_user = (item.descripcion_usuario or item.descripcion_articulo or "").strip() or "—"
        search_parts = [
            item.codigo_proceso,
            contract.unidad_compra if contract else "",
            contract.descripcion if contract else "",
            item.descripcion_articulo,
            item.descripcion_usuario,
            contract.razon_social if contract else "",
            proceso_meta.get("modalidad", ""),
            proceso_meta.get("objeto_proceso", ""),
        ]
        search_text = normalize_text(" ".join(p for p in search_parts if p))

        result = await self.db.execute(
            select(DGCPHistoricalAward).where(
                DGCPHistoricalAward.tenant_id == self.tenant_id,
                DGCPHistoricalAward.process_code == item.codigo_proceso,
                DGCPHistoricalAward.contract_code == item.codigo_contrato,
                DGCPHistoricalAward.item_description_user == item_desc_user,
            )
        )
        row = result.scalar_one_or_none()
        fields = {
            "buyer_institution": contract.unidad_compra if contract else "—",
            "buyer_institution_code": str(contract.codigo_unidad_compra) if contract and contract.codigo_unidad_compra else None,
            "award_date": award_date,
            "contract_object": contract.descripcion if contract else None,
            "item_description": item.descripcion_articulo,
            "supplier_name": contract.razon_social if contract else None,
            "supplier_rpe": contract.rpe if contract else None,
            "awarded_amount": Decimal(str(contract.valor_contratado)) if contract else None,
            "currency": contract.divisa if contract else "DOP",
            "quantity": Decimal(str(item.cantidad or 0)),
            "unit_price": Decimal(str(item.precio_unitario or 0)),
            "total_line_amount": Decimal(str(item.costo_total or 0)),
            "unit_measure": item.unidad_medida,
            "modality": proceso_meta.get("modalidad"),
            "objeto_proceso": proceso_meta.get("objeto_proceso"),
            "award_status": contract.estado_adjudicacion if contract else None,
            "contract_url": contract.url_contrato if contract else None,
            "process_url": proceso_meta.get("source_url"),
            "source": "dgcp_contratos_articulos",
            "unspsc_family": item.familia,
            "unspsc_class": item.clase,
            "unspsc_subclass": item.subclase,
            "search_text": search_text,
            "raw_payload": {
                "contrato_articulo": item.model_dump(mode="json"),
                "contrato": contract.model_dump(mode="json") if contract else {},
                "proceso_meta": {
                    **proceso_meta,
                    "publication_date": publication_date.isoformat() if isinstance(publication_date, datetime) else None,
                    "publication_to_award_days": publication_to_award_days,
                },
            },
            "indexed_at": datetime.now(UTC),
        }

        if row:
            for k, v in fields.items():
                setattr(row, k, v)
            return False

        self.db.add(
            DGCPHistoricalAward(
                tenant_id=self.tenant_id,
                process_code=item.codigo_proceso,
                contract_code=item.codigo_contrato,
                item_description_user=item_desc_user,
                **fields,
            )
        )
        await self.db.flush()
        return True

    async def _get_contract(self, process_code: str, contract_code: str) -> DGCPContratoRecord | None:
        key = f"{process_code}:{contract_code}"
        cached = self._contracts_cache.get(key)
        if cached:
            return cached
        return await self._ensure_contract(process_code, contract_code)

    async def _proceso_meta(self, process_code: str) -> dict:
        if process_code in self._proceso_meta_cache:
            return self._proceso_meta_cache[process_code]

        result = await self.db.execute(
            select(DGCPOpportunity).where(
                DGCPOpportunity.tenant_id == self.tenant_id,
                DGCPOpportunity.code == process_code,
            )
        )
        opp = result.scalar_one_or_none()
        if opp:
            pub = None
            if isinstance(opp.full_info, dict):
                pub = opp.full_info.get("fecha_publicacion")
            meta = {
                "modalidad": opp.modalidad,
                "objeto_proceso": opp.objeto_proceso,
                "source_url": opp.source_url,
                "publication_date": pub,
            }
            self._proceso_meta_cache[process_code] = meta
            return meta

        try:
            response = await self.client.fetch_procesos(
                page=1,
                limit=1,
                proceso=process_code,
                estado_proceso=None,
            )
            if response.content and isinstance(response.content[0], DGCPProcesoRecord):
                proceso = response.content[0]
                meta = {
                    "modalidad": proceso.modalidad,
                    "objeto_proceso": proceso.objeto_proceso,
                    "source_url": proceso.url,
                    "publication_date": proceso.fecha_publicacion,
                }
                self._proceso_meta_cache[process_code] = meta
                return meta
        except Exception:
            pass

        meta: dict = {}
        self._proceso_meta_cache[process_code] = meta
        return meta

    async def count_institution_rows(
        self,
        institution_name: str,
        institution_code: str | int | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(DGCPHistoricalAward).where(
            DGCPHistoricalAward.tenant_id == self.tenant_id,
            DGCPHistoricalAward.contract_url.isnot(None),
        )
        if institution_code is not None:
            stmt = stmt.where(DGCPHistoricalAward.buyer_institution_code == str(institution_code))
        else:
            stmt = stmt.where(DGCPHistoricalAward.buyer_institution == institution_name)
        total = await self.db.scalar(stmt)
        if total:
            return int(total)

        if institution_code is None:
            return 0

        rows = await self.db.execute(
            select(DGCPHistoricalAward.buyer_institution).where(
                DGCPHistoricalAward.tenant_id == self.tenant_id,
                DGCPHistoricalAward.contract_url.isnot(None),
            )
        )
        count = 0
        for (buyer,) in rows.all():
            if institution_matches_strict(
                institution_name,
                buyer,
                query_institution_code=institution_code,
            ):
                count += 1
        return count
