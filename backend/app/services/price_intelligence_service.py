"""Price Intelligence — búsqueda, comparación y detalle sobre productos indexados."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_list import PriceListFile, PriceListProduct
from app.schemas.prices import (
    PriceCompareAlternative,
    PriceCompareResponse,
    PriceProductDetailResponse,
    PriceProductResponse,
    PriceSearchResponse,
)
from app.services.price_classification import is_laptop_product

MIN_LAPTOP_COMPARE_PRICE = Decimal("100")
MIN_DESKTOP_COMPARE_PRICE = Decimal("50")


@dataclass
class PriceSearchFilters:
    q: str | None = None
    brand: str | None = None
    supplier: str | None = None
    manufacturer: str | None = None
    category: str | None = None
    product_type: str | None = None
    ram_gb: int | None = None
    storage_gb: int | None = None
    processor: str | None = None
    display: str | None = None
    operating_system: str | None = None
    price_min: Decimal | None = None
    price_max: Decimal | None = None
    currency: str | None = None
    stock_min: int | None = None
    stock_disponible: bool | None = None
    list_date_from: datetime | None = None
    list_date_to: datetime | None = None
    commercial_only: bool = True
    limit: int = 50


class PriceIntelligenceService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    def _base_query(self):
        return (
            select(PriceListProduct, PriceListFile.file_date_estimated)
            .join(PriceListFile, PriceListProduct.file_id == PriceListFile.id)
            .where(
                PriceListProduct.tenant_id == self.tenant_id,
                PriceListProduct.is_current.is_(True),
                PriceListFile.is_current.is_(True),
            )
        )

    def _apply_filters(self, stmt, filters: PriceSearchFilters):
        if filters.commercial_only:
            stmt = stmt.where(PriceListProduct.is_commercial.is_(True))

        if filters.q:
            q = filters.q.strip().lower()
            laptop_synonyms = {"laptop", "laptops", "notebook", "notebooks", "portatil", "portátil"}
            if q in laptop_synonyms:
                stmt = stmt.where(
                    PriceListProduct.product_type == "laptop",
                    PriceListProduct.excluded_from_laptop.is_(False),
                )
            else:
                term = f"%{filters.q.strip()}%"
                stmt = stmt.where(
                    or_(
                        PriceListProduct.search_blob.ilike(term),
                        PriceListProduct.description.ilike(term),
                        PriceListProduct.sku.ilike(term),
                        PriceListProduct.mpn.ilike(term),
                        PriceListProduct.model.ilike(term),
                        PriceListProduct.brand.ilike(term),
                    )
                )

        if filters.product_type:
            stmt = stmt.where(PriceListProduct.product_type == filters.product_type.lower())
            if filters.product_type.lower() in ("laptop", "laptops"):
                stmt = stmt.where(PriceListProduct.excluded_from_laptop.is_(False))
        elif filters.category:
            cat = filters.category.strip().lower()
            if cat in ("laptop", "laptops", "notebook", "notebooks"):
                stmt = stmt.where(
                    PriceListProduct.product_type == "laptop",
                    PriceListProduct.excluded_from_laptop.is_(False),
                )
            else:
                stmt = stmt.where(
                    or_(
                        PriceListProduct.product_type.ilike(f"%{cat}%"),
                        PriceListProduct.category.ilike(f"%{cat}%"),
                    )
                )

        if filters.brand:
            stmt = stmt.where(PriceListProduct.brand.ilike(f"%{filters.brand.strip()}%"))
        if filters.supplier:
            stmt = stmt.where(PriceListProduct.supplier.ilike(f"%{filters.supplier.strip()}%"))
        if filters.manufacturer:
            stmt = stmt.where(PriceListProduct.manufacturer.ilike(f"%{filters.manufacturer.strip()}%"))
        if filters.ram_gb is not None:
            stmt = stmt.where(PriceListProduct.ram_gb == filters.ram_gb)
        if filters.storage_gb is not None:
            stmt = stmt.where(PriceListProduct.storage_gb == filters.storage_gb)
        if filters.processor:
            stmt = stmt.where(PriceListProduct.processor.ilike(f"%{filters.processor.strip()}%"))
        if filters.display:
            stmt = stmt.where(PriceListProduct.display.ilike(f"%{filters.display.strip()}%"))
        if filters.operating_system:
            stmt = stmt.where(PriceListProduct.operating_system.ilike(f"%{filters.operating_system.strip()}%"))

        price_col = PriceListProduct.preferred_price
        if filters.price_min is not None:
            stmt = stmt.where(price_col >= filters.price_min)
        if filters.price_max is not None:
            stmt = stmt.where(price_col <= filters.price_max)
        if filters.currency:
            stmt = stmt.where(PriceListProduct.currency == filters.currency.upper())
        if filters.stock_min is not None:
            stmt = stmt.where(and_(PriceListProduct.stock.is_not(None), PriceListProduct.stock >= filters.stock_min))
        if filters.stock_disponible:
            stmt = stmt.where(and_(PriceListProduct.stock.is_not(None), PriceListProduct.stock > 0))
        if filters.list_date_from:
            stmt = stmt.where(PriceListProduct.source_file_date >= filters.list_date_from)
        if filters.list_date_to:
            stmt = stmt.where(PriceListProduct.source_file_date <= filters.list_date_to)
        return stmt

    def _to_response(self, row: PriceListProduct, date_estimated: bool = True) -> PriceProductResponse:
        data = PriceProductResponse.model_validate(row)
        data.source_file_date_estimated = date_estimated
        return data

    async def search(self, filters: PriceSearchFilters) -> PriceSearchResponse:
        stmt = self._apply_filters(self._base_query(), filters)
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(
            PriceListProduct.preferred_price.asc().nulls_last(),
            PriceListProduct.stock.desc().nulls_last(),
        ).limit(min(filters.limit, 200))

        rows = (await self.db.execute(stmt)).all()
        items = [self._to_response(p, est) for p, est in rows]
        return PriceSearchResponse(query=filters.q, total=total, items=items)

    async def get_product(self, product_id: uuid.UUID) -> PriceProductDetailResponse | None:
        row = (
            await self.db.execute(
                self._base_query().where(PriceListProduct.id == product_id)
            )
        ).first()
        if not row:
            return None
        product, date_estimated = row
        base = self._to_response(product, date_estimated)
        warning = None
        if not product.is_cotizable:
            warning = (
                "Esta línea parece garantía/servicio/accesorio, no producto principal. "
                "Revise antes de cotizar."
            )
        detail = PriceProductDetailResponse(
            **base.model_dump(),
            raw_row_json=product.raw_row_json or {},
            raw_columns_json=product.raw_columns_json or [],
            comparison_price_label=(
                f"Precio usado para comparación ({product.preferred_price_field or 'precio'})"
                if product.price_review_status == "ok"
                else "Precio requiere revisión — no usar para comparación automática"
            ),
            cotizable_warning=warning,
        )
        return detail

    async def compare(self, filters: PriceSearchFilters, *, question: str) -> PriceCompareResponse:
        filters.commercial_only = True
        filters.limit = 200

        target_laptop = (
            (filters.product_type or "").lower() in ("laptop", "laptops")
            or (filters.category or "").lower() in ("laptop", "laptops", "notebook")
            or (filters.q or "").lower() in ("laptop", "laptops", "notebook")
            or (filters.ram_gb is not None and filters.storage_gb is not None)
        )
        if target_laptop and filters.price_min is None:
            filters.price_min = MIN_LAPTOP_COMPARE_PRICE
            filters.product_type = "laptop"

        result = await self.search(filters)
        warnings: list[str] = []

        candidates = [
            p for p in result.items
            if p.preferred_price is not None
            and p.price_review_status == "ok"
            and (
                not target_laptop
                or is_laptop_product(
                    p.description,
                    p.category,
                    p.product_type,
                    source_sheet=p.source_sheet,
                    excluded_from_laptop=p.excluded_from_laptop,
                    ram_gb=p.ram_gb,
                    storage_gb=p.storage_gb,
                )
            )
        ]

        if target_laptop:
            candidates = [p for p in candidates if (p.preferred_price or 0) >= MIN_LAPTOP_COMPARE_PRICE]

        if not candidates:
            return PriceCompareResponse(
                question=question,
                best_supplier=None,
                best_product=None,
                alternatives=[],
                warnings=["No se encontraron productos comerciales que coincidan."],
                summary="No hay opciones indexadas en hojas comerciales para esta consulta.",
            )

        in_stock = [p for p in candidates if (p.stock or 0) > 0]
        ranked = in_stock or candidates
        if not in_stock:
            warnings.append("Ninguna opción tiene stock confirmado en la lista.")

        best = ranked[0]
        file_meta: dict[uuid.UUID, tuple] = {}
        file_ids = {p.file_id for p in ranked[:20]}
        if file_ids:
            files = (
                await self.db.execute(select(PriceListFile).where(PriceListFile.id.in_(file_ids)))
            ).scalars().all()
            file_meta = {f.id: (f.file_modified_at, f.file_date_estimated) for f in files}

        alternatives: list[PriceCompareAlternative] = []
        seen: set[str] = set()
        for item in ranked[1:10]:
            key = f"{(item.supplier or '').lower()}|{item.sku or item.description}"
            if key in seen:
                continue
            seen.add(key)
            fdate, fest = file_meta.get(item.file_id, (item.source_file_date, True))
            alternatives.append(
                PriceCompareAlternative(
                    supplier=item.supplier,
                    brand=item.brand,
                    description=item.description,
                    sku=item.sku,
                    price=item.preferred_price,
                    preferred_price=item.preferred_price,
                    currency=item.currency,
                    stock=item.stock,
                    source_filename=item.source_filename,
                    source_sheet=item.source_sheet,
                    source_row=item.source_row,
                    file_date=fdate or item.source_file_date,
                    file_date_estimated=fest,
                )
            )

        best_date, best_est = file_meta.get(best.file_id, (best.source_file_date, best.source_file_date_estimated))
        date_label = best_date.strftime("%d/%m/%Y") if best_date else "sin fecha"
        if best_est:
            date_label += " (estimada por modificación del archivo)"

        summary = (
            f"Mejor opción: {best.supplier or '—'} — {best.description or best.sku} "
            f"por {best.currency} {best.preferred_price} "
            f"({'stock ' + str(best.stock) if best.stock else 'sin stock confirmado'}). "
            f"Fuente: {best.source_filename} / {best.source_sheet} fila {best.source_row}. "
            f"Lista del {date_label}."
        )

        return PriceCompareResponse(
            question=question,
            best_supplier=best.supplier,
            best_product=best,
            alternatives=alternatives,
            warnings=warnings,
            summary=summary,
        )

    async def list_supplier_files(self, supplier: str, *, limit: int = 20) -> list[PriceListFile]:
        stmt = (
            select(PriceListFile)
            .where(
                PriceListFile.tenant_id == self.tenant_id,
                PriceListFile.is_current.is_(True),
                or_(
                    PriceListFile.supplier.ilike(f"%{supplier}%"),
                    PriceListFile.manufacturer.ilike(f"%{supplier}%"),
                    PriceListFile.filename.ilike(f"%{supplier}%"),
                ),
            )
            .order_by(PriceListFile.indexed_at.desc())
            .limit(limit)
        )
        return list((await self.db.execute(stmt)).scalars().all())
