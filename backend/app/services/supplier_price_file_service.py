"""Procesa listas de precios desde OneDrive ENTRADAS → indexación → PROCESADOS."""

from __future__ import annotations

import hashlib
import tempfile
import uuid
from dataclasses import asdict
from datetime import UTC, datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_settings import IntegrationRepositoryBinding
from app.models.m365_repository import M365RepositoryFile
from app.models.price_list import PriceListFile, PriceListProduct
from app.services.price_list_parser import PriceListParser
from app.services.price_normalizer import detect_brand, detect_supplier_from_path
from app.services.price_sheet_policy import PARSER_VERSION

SUPPORTED = {".xlsx", ".xls", ".csv"}


class SupplierPriceFileService:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.parser = PriceListParser()

    async def process_inbox(self, binding_id: uuid.UUID) -> dict:
        pending = await self._pending_files(binding_id)
        indexed = 0
        errors: list[str] = []
        processed_ids: list[str] = []

        for file_row in pending:
            try:
                count = await self._index_file(file_row)
                indexed += count
                processed_ids.append(file_row.graph_item_id)
                file_row.tags = list(set((file_row.tags or []) + ["price_processed"]))
            except Exception as exc:
                errors.append(f"{file_row.name}: {exc}")

        await self.db.commit()
        return {
            "records_indexed": indexed,
            "files_processed": len(processed_ids),
            "errors": errors,
            "message": f"{len(processed_ids)} listas procesadas, {indexed} productos indexados",
        }

    async def list_pending(self, binding_id: uuid.UUID | None = None) -> list[dict]:
        q = select(M365RepositoryFile).where(
            M365RepositoryFile.tenant_id == self.tenant_id,
            M365RepositoryFile.is_folder.is_(False),
            M365RepositoryFile.is_deleted.is_(False),
        )
        if binding_id:
            q = q.where(M365RepositoryFile.binding_id == binding_id)
        else:
            q = q.where(M365RepositoryFile.parent_path.ilike("%ENTRADAS%"))
        rows = (await self.db.execute(q)).scalars().all()
        out = []
        for r in rows:
            if Path(r.name).suffix.lower() not in SUPPORTED:
                continue
            if "price_processed" in (r.tags or []):
                continue
            out.append({
                "id": str(r.id),
                "name": r.name,
                "parent_path": r.parent_path,
                "graph_item_id": r.graph_item_id,
                "modified_at": r.modified_at_graph.isoformat() if r.modified_at_graph else None,
            })
        return out

    async def _pending_files(self, binding_id: uuid.UUID) -> list[M365RepositoryFile]:
        rows = (
            await self.db.execute(
                select(M365RepositoryFile).where(
                    M365RepositoryFile.tenant_id == self.tenant_id,
                    M365RepositoryFile.binding_id == binding_id,
                    M365RepositoryFile.is_folder.is_(False),
                    M365RepositoryFile.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        pending = []
        for r in rows:
            if Path(r.name).suffix.lower() not in SUPPORTED:
                continue
            if "price_processed" in (r.tags or []):
                continue
            existing = (
                await self.db.execute(
                    select(PriceListFile).where(
                        PriceListFile.tenant_id == self.tenant_id,
                        PriceListFile.graph_file_id == r.graph_item_id,
                        PriceListFile.is_current.is_(True),
                        PriceListFile.status == "indexed",
                    )
                )
            ).scalar_one_or_none()
            if existing:
                r.tags = list(set((r.tags or []) + ["price_processed"]))
                continue
            pending.append(r)
        return pending

    async def _index_file(self, file_row: M365RepositoryFile) -> int:
        download_url = file_row.download_url
        if not download_url and self.user_id and file_row.graph_item_id:
            from app.services.m365_graph_session import M365GraphSessionService

            sess = await M365GraphSessionService(self.db, self.tenant_id, self.user_id).session_for_account()
            download_url = await sess.client.onedrive.get_download_url(file_row.graph_item_id)
            file_row.download_url = download_url

        if not download_url:
            raise ValueError("Sin URL de descarga")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(download_url)
            resp.raise_for_status()
            content = resp.content

        content_hash = hashlib.sha256(content).hexdigest() + f":{PARSER_VERSION}"
        rel = f"onedrive/{file_row.parent_path}/{file_row.name}".strip("/")

        existing = (
            await self.db.execute(
                select(PriceListFile).where(
                    PriceListFile.tenant_id == self.tenant_id,
                    PriceListFile.graph_file_id == file_row.graph_item_id,
                    PriceListFile.is_current.is_(True),
                )
            )
        ).scalar_one_or_none()
        if existing and existing.content_hash == content_hash:
            return existing.total_records

        with tempfile.NamedTemporaryFile(suffix=Path(file_row.name).suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            parsed = self.parser.parse_file(tmp_path, relative_path=rel)
        finally:
            tmp_path.unlink(missing_ok=True)

        if parsed.errors and not parsed.rows:
            raise ValueError("; ".join(parsed.errors))

        supplier = parsed.supplier or detect_supplier_from_path(rel, file_row.name)
        manufacturer = parsed.manufacturer or detect_brand(file_row.name, supplier)
        now = datetime.now(UTC)
        file_modified = file_row.modified_at_graph or now
        audit_payload = [asdict(a) for a in parsed.sheet_audits]

        version = 1
        if existing:
            version = existing.version + 1
            await self.db.execute(
                update(PriceListFile).where(PriceListFile.id == existing.id).values(is_current=False)
            )
            await self.db.execute(
                update(PriceListProduct).where(PriceListProduct.file_id == existing.id).values(is_current=False)
            )

        file_rec = PriceListFile(
            tenant_id=self.tenant_id,
            supplier=supplier,
            manufacturer=manufacturer,
            filename=file_row.name,
            relative_path=rel,
            file_modified_at=file_modified,
            file_date_estimated=False,
            indexed_at=now,
            content_hash=content_hash,
            version=version,
            total_records=len(parsed.rows),
            status="indexed" if parsed.rows else "empty",
            errors=parsed.errors,
            audit_json=audit_payload,
            is_current=True,
            graph_file_id=file_row.graph_item_id,
            processing_status="processed",
        )
        self.db.add(file_rec)
        await self.db.flush()

        batch: list[PriceListProduct] = []
        for row in parsed.rows:
            batch.append(
                PriceListProduct(
                    tenant_id=self.tenant_id,
                    file_id=file_rec.id,
                    version=version,
                    is_current=True,
                    supplier=supplier,
                    manufacturer=row.brand or manufacturer,
                    sku=row.sku,
                    mpn=row.mpn,
                    model=row.model,
                    description=row.description,
                    category=row.category,
                    product_type=row.product_type,
                    brand=row.brand,
                    processor=row.processor,
                    ram_gb=row.ram_gb,
                    storage_gb=row.storage_gb,
                    storage_type=row.storage_type,
                    display=row.display,
                    operating_system=row.operating_system,
                    price=row.preferred_price,
                    preferred_price=row.preferred_price,
                    preferred_price_field=row.preferred_price_field,
                    price_regular=row.price_regular,
                    price_rebate=row.price_rebate,
                    price_discount=row.price_discount,
                    prices_original=row.prices_original,
                    currency=row.currency or "USD",
                    stock=row.stock,
                    in_transit=row.in_transit,
                    stock_text_original=row.stock_text_original,
                    warranty=row.warranty,
                    raw_row_json=row.raw_row_json,
                    raw_columns_json=row.raw_columns_json,
                    search_blob=row.search_blob,
                    is_commercial=row.is_commercial,
                    excluded_from_laptop=row.excluded_from_laptop,
                    is_cotizable=row.is_cotizable,
                    price_review_status=row.price_review_status,
                    classification_label=row.classification_label,
                    stock_source_column=row.stock_source_column,
                    source_filename=file_row.name,
                    source_sheet=row.sheet_name,
                    source_row=row.row_number,
                    source_file_date=file_modified,
                    indexed_at=now,
                )
            )
            if len(batch) >= 500:
                self.db.add_all(batch)
                await self.db.flush()
                batch.clear()
        if batch:
            self.db.add_all(batch)

        from app.services.supplier_service import SupplierService

        try:
            await SupplierService(self.db, self.tenant_id).auto_link_price_file(file_rec.id)
        except Exception:
            pass

        return len(parsed.rows)

    async def resolve_processed_binding(self) -> IntegrationRepositoryBinding | None:
        result = await self.db.execute(
            select(IntegrationRepositoryBinding).where(
                IntegrationRepositoryBinding.tenant_id == self.tenant_id,
                IntegrationRepositoryBinding.folder_key == "03_PROVEEDORES_PROCESADOS",
            )
        )
        return result.scalar_one_or_none()
