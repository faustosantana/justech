"""PriceListIndexer — indexación con auditoría y preservación de fila original."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.price_list import PriceListFile, PriceListProduct
from app.services.price_list_parser import PriceListParser
from app.services.price_normalizer import detect_brand, detect_supplier_from_path
from app.services.price_sheet_policy import PARSER_VERSION


@dataclass
class PriceSyncReport:
    started_at: datetime
    finished_at: datetime | None = None
    files_detected: int = 0
    files_new: int = 0
    files_unchanged: int = 0
    files_updated: int = 0
    records_created: int = 0
    errors: list[str] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)
    audit_summary: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> int:
        end = self.finished_at or datetime.now(timezone.utc)
        return int((end - self.started_at).total_seconds() * 1000)


class PriceListIndexer:
    SCAN_SUBFOLDERS = frozenset({"ENTRADAS", "PROCESADOS", "LISTAS_PRECIOS", "LISTAS PRECIOS"})

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.parser = PriceListParser()

    def _source_root(self) -> Path:
        return Path(settings.knowledge_source_path)

    def discover_files(self) -> list[Path]:
        root = self._source_root() / settings.price_list_root_folder
        if not root.is_dir():
            return []
        found: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file() or path.name.startswith("."):
                continue
            if path.suffix.lower() not in PriceListParser.SUPPORTED:
                continue
            rel_parts = path.relative_to(self._source_root()).parts
            if len(rel_parts) >= 2:
                sub = rel_parts[1].upper()
                if sub not in self.SCAN_SUBFOLDERS and not settings.price_list_scan_all_subfolders:
                    continue
            found.append(path)
        return sorted(found)

    @staticmethod
    def file_hash(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                h.update(block)
        return f"{h.hexdigest()}:{PARSER_VERSION}"

    async def sync(self) -> PriceSyncReport:
        report = PriceSyncReport(started_at=datetime.now(timezone.utc))
        paths = self.discover_files()
        report.files_detected = len(paths)
        total_laptops = 0
        total_with_price = 0
        total_with_stock = 0

        for path in paths:
            rel = str(path.relative_to(self._source_root())).replace("\\", "/")
            content_hash = self.file_hash(path)
            existing = (
                await self.db.execute(
                    select(PriceListFile).where(
                        PriceListFile.tenant_id == self.tenant_id,
                        PriceListFile.relative_path == rel,
                        PriceListFile.is_current.is_(True),
                    )
                )
            ).scalar_one_or_none()

            if existing and existing.content_hash == content_hash:
                report.files_unchanged += 1
                report.files.append({
                    "path": rel,
                    "status": "unchanged",
                    "records": existing.total_records,
                })
                continue

            parsed = self.parser.parse_file(path, relative_path=rel)
            audit_payload = [asdict(a) for a in parsed.sheet_audits]

            if parsed.errors and not parsed.rows:
                report.errors.extend([f"{rel}: {e}" for e in parsed.errors])
                report.files.append({
                    "path": rel,
                    "status": "error",
                    "errors": parsed.errors,
                    "audit": audit_payload,
                })
                continue

            version = 1
            if existing:
                version = existing.version + 1
                await self.db.execute(
                    update(PriceListFile).where(PriceListFile.id == existing.id).values(is_current=False)
                )
                await self.db.execute(
                    update(PriceListProduct).where(PriceListProduct.file_id == existing.id).values(is_current=False)
                )
                report.files_updated += 1
            else:
                report.files_new += 1

            supplier = parsed.supplier or detect_supplier_from_path(rel, path.name)
            manufacturer = parsed.manufacturer or detect_brand(path.name, supplier)
            stat = path.stat()
            file_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            now = datetime.now(timezone.utc)

            file_row = PriceListFile(
                tenant_id=self.tenant_id,
                supplier=supplier,
                manufacturer=manufacturer,
                filename=path.name,
                relative_path=rel,
                file_modified_at=file_modified,
                file_date_estimated=True,
                indexed_at=now,
                content_hash=content_hash,
                version=version,
                total_records=len(parsed.rows),
                status="indexed" if parsed.rows else "empty",
                errors=parsed.errors,
                audit_json=audit_payload,
                is_current=True,
            )
            self.db.add(file_row)
            await self.db.flush()

            batch: list[PriceListProduct] = []
            for row in parsed.rows:
                batch.append(
                    PriceListProduct(
                        tenant_id=self.tenant_id,
                        file_id=file_row.id,
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
                        source_filename=path.name,
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
                await self.db.flush()

            total_laptops += parsed.laptops_count
            total_with_price += parsed.with_price_count
            total_with_stock += parsed.with_stock_count
            report.records_created += len(parsed.rows)
            report.files.append({
                "path": rel,
                "status": "indexed",
                "version": version,
                "records": len(parsed.rows),
                "laptops": parsed.laptops_count,
                "with_price": parsed.with_price_count,
                "with_stock": parsed.with_stock_count,
                "errors": parsed.errors,
                "audit": audit_payload,
            })

        await self.db.commit()
        report.finished_at = datetime.now(timezone.utc)
        report.audit_summary = {
            "total_laptops": total_laptops,
            "total_with_price": total_with_price,
            "total_with_stock": total_with_stock,
            "parser_version": PARSER_VERSION,
        }
        return report
