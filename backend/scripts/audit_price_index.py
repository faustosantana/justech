#!/usr/bin/env python3
"""Auditoría de indexación de precios — genera .qa/price-index-audit.md"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.price_list import PriceListFile, PriceListProduct
from app.models.tenant import Tenant
from app.services.price_list_parser import PriceListParser
from app.services.price_sheet_policy import PARSER_VERSION


def _audit_file_markdown(path: Path, rel: str, parsed, stat) -> list[str]:
    lines = [
        f"### {path.name}",
        "",
        f"- **Ruta:** `{rel}`",
        f"- **Fecha archivo (mtime):** {datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} *(estimada por modificación)*",
        f"- **Proveedor detectado:** {parsed.supplier or '—'}",
        f"- **Fabricante:** {parsed.manufacturer or '—'}",
        f"- **Productos indexables (parser):** {len(parsed.rows)}",
        f"- **Laptops detectadas:** {parsed.laptops_count}",
        f"- **Con precio:** {parsed.with_price_count}",
        f"- **Con stock:** {parsed.with_stock_count}",
        "",
        "#### Hojas",
        "",
    ]
    for audit in parsed.sheet_audits:
        lines.append(f"**{audit.sheet_name}** — `{audit.status}`")
        if audit.reason:
            lines.append(f"- Motivo: {audit.reason}")
        lines.append(f"- Header fila: {audit.header_row}")
        lines.append(f"- Columnas: `{audit.columns_mapped}`")
        lines.append(f"- Filas leídas: {audit.rows_read} | válidas: {audit.rows_valid} | descartadas: {audit.rows_discarded}")
        if audit.discard_reasons:
            lines.append(f"- Descartes: {audit.discard_reasons}")
        lines.append("")
    if parsed.errors:
        lines.extend(["#### Errores", ""])
        for err in parsed.errors:
            lines.append(f"- {err}")
        lines.append("")
    return lines


async def run(*, tenant_slug: str, report_path: Path, root_override: Path | None = None) -> int:
    parser = PriceListParser()
    source_root = root_override or Path(settings.knowledge_source_path)
    folder = source_root / settings.price_list_root_folder

    lines = [
        "# Price Index Audit",
        "",
        f"**Generado:** {datetime.now(timezone.utc).isoformat()}",
        f"**Parser:** {PARSER_VERSION}",
        f"**Carpeta:** `{folder}`",
        "",
    ]

    files = sorted(folder.rglob("*")) if folder.is_dir() else []
    files = [p for p in files if p.is_file() and p.suffix.lower() in PriceListParser.SUPPORTED]

    total_rows = 0
    total_laptops = 0
    for path in files:
        rel = str(path.relative_to(source_root)).replace("\\", "/")
        parsed = parser.parse_file(path, relative_path=rel)
        stat = path.stat()
        lines.extend(_audit_file_markdown(path, rel, parsed, stat))
        total_rows += len(parsed.rows)
        total_laptops += parsed.laptops_count

    lines.extend([
        "## Totales (parser dry-run)",
        "",
        f"- Archivos: **{len(files)}**",
        f"- Productos indexables: **{total_rows}**",
        f"- Laptops: **{total_laptops}**",
        "",
    ])

    async with AsyncSessionLocal() as session:
        tenant = (await session.execute(select(Tenant).where(Tenant.slug == tenant_slug))).scalar_one_or_none()
        if tenant:
            db_files = (await session.execute(
                select(func.count()).select_from(PriceListFile).where(
                    PriceListFile.tenant_id == tenant.id, PriceListFile.is_current.is_(True)
                )
            )).scalar_one()
            db_products = (await session.execute(
                select(func.count()).select_from(PriceListProduct).where(
                    PriceListProduct.tenant_id == tenant.id, PriceListProduct.is_current.is_(True)
                )
            )).scalar_one()
            db_laptops = (await session.execute(
                select(func.count()).select_from(PriceListProduct).where(
                    PriceListProduct.tenant_id == tenant.id,
                    PriceListProduct.is_current.is_(True),
                    PriceListProduct.product_type == "laptop",
                )
            )).scalar_one()
            lines.extend([
                "## Estado BD (tenant actual)",
                "",
                f"- Archivos indexados: **{db_files}**",
                f"- Productos en BD: **{db_products}**",
                f"- Laptops en BD: **{db_laptops}**",
                "",
            ])

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Audit report: {report_path}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tenant", default="justech")
    ap.add_argument("--report", default=".qa/price-index-audit.md")
    args = ap.parse_args()
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = Path.cwd() / report_path
    raise SystemExit(asyncio.run(run(tenant_slug=args.tenant, report_path=report_path)))


if __name__ == "__main__":
    main()
