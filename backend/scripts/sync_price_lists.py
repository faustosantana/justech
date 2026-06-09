#!/usr/bin/env python3
"""Sincroniza listas de precios desde 03_PROVEEDORES hacia BD estructurada."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.tenant import Tenant
from app.services.price_list_indexer import PriceListIndexer


def _write_report(report, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Price Sync Report",
        "",
        f"**Generado:** {datetime.now(timezone.utc).isoformat()}",
        f"**Carpeta fuente:** `{settings.knowledge_source_path}/{settings.price_list_root_folder}`",
        "",
        "## Resumen",
        "",
        f"- Archivos detectados: **{report.files_detected}**",
        f"- Archivos nuevos: **{report.files_new}**",
        f"- Sin cambio (hash): **{report.files_unchanged}**",
        f"- Actualizados (nueva versión): **{report.files_updated}**",
        f"- Registros creados: **{report.records_created}**",
        f"- Tiempo: **{report.duration_ms} ms**",
        "",
    ]
    if report.errors:
        lines.extend(["## Errores", ""])
        for err in report.errors:
            lines.append(f"- {err}")
        lines.append("")

    lines.extend(["## Archivos", ""])
    for item in report.files:
        status = item.get("status", "?")
        path = item.get("path", "—")
        extra = ""
        if item.get("records") is not None:
            extra = f" — {item['records']} registros"
        if item.get("version"):
            extra += f" (v{item['version']})"
        lines.append(f"- `{path}` — **{status}**{extra}")
        for err in item.get("errors") or []:
            lines.append(f"  - ⚠ {err}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run(*, tenant_slug: str, report_path: Path) -> int:
    async with AsyncSessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        ).scalar_one_or_none()
        if not tenant:
            print(f"Tenant no encontrado: {tenant_slug}", file=sys.stderr)
            return 1

        indexer = PriceListIndexer(session, tenant.id)
        report = await indexer.sync()
        _write_report(report, report_path)

        print(f"Detectados: {report.files_detected}")
        print(f"Nuevos: {report.files_new} | Sin cambio: {report.files_unchanged} | Actualizados: {report.files_updated}")
        print(f"Registros: {report.records_created} | {report.duration_ms} ms")
        print(f"Reporte: {report_path}")
        if report.errors:
            print(f"Errores: {len(report.errors)}", file=sys.stderr)
            return 2
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexar listas de precios JAIOS")
    parser.add_argument("--tenant", default="justech", help="Slug del tenant")
    parser.add_argument(
        "--report",
        default=".qa/prices-sync-report.md",
        help="Ruta del reporte markdown",
    )
    args = parser.parse_args()
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = Path.cwd() / report_path
    code = asyncio.run(run(tenant_slug=args.tenant, report_path=report_path))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
