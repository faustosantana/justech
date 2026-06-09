#!/usr/bin/env python3
"""Auditoría de clasificación laptop — Price Intelligence v2.2."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, or_, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import AsyncSessionLocal
from app.models.price_list import PriceListProduct
from app.models.tenant import Tenant
from app.services.price_classification import contains_non_laptop_keyword


KEEP_YOUR_HD = "1Y Keep Your HD"


async def run(report_path: Path) -> int:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).limit(1))).scalar_one_or_none()
        if not tenant:
            print("No tenant", file=sys.stderr)
            return 1
        tid = tenant.id

        total_laptop_type = await db.scalar(
            select(func.count()).select_from(PriceListProduct).where(
                PriceListProduct.tenant_id == tid,
                PriceListProduct.is_current.is_(True),
                PriceListProduct.product_type == "laptop",
            )
        )
        true_laptops = await db.scalar(
            select(func.count()).select_from(PriceListProduct).where(
                PriceListProduct.tenant_id == tid,
                PriceListProduct.is_current.is_(True),
                PriceListProduct.product_type == "laptop",
                PriceListProduct.excluded_from_laptop.is_(False),
            )
        )
        excluded = await db.scalar(
            select(func.count()).select_from(PriceListProduct).where(
                PriceListProduct.tenant_id == tid,
                PriceListProduct.is_current.is_(True),
                PriceListProduct.excluded_from_laptop.is_(True),
                or_(
                    PriceListProduct.product_type == "laptop",
                    PriceListProduct.source_sheet.ilike("%warrant%"),
                ),
            )
        )

        keep_hd_rows = (
            await db.execute(
                select(PriceListProduct).where(
                    PriceListProduct.tenant_id == tid,
                    PriceListProduct.is_current.is_(True),
                    PriceListProduct.description.ilike(f"%{KEEP_YOUR_HD}%"),
                )
            )
        ).scalars().all()

        warranty_as_laptop = (
            await db.execute(
                select(PriceListProduct).where(
                    PriceListProduct.tenant_id == tid,
                    PriceListProduct.is_current.is_(True),
                    PriceListProduct.source_sheet.ilike("%warrant%"),
                    PriceListProduct.product_type == "laptop",
                    PriceListProduct.excluded_from_laptop.is_(False),
                ).limit(10)
            )
        ).scalars().all()

        valid_samples = (
            await db.execute(
                select(PriceListProduct).where(
                    PriceListProduct.tenant_id == tid,
                    PriceListProduct.is_current.is_(True),
                    PriceListProduct.product_type == "laptop",
                    PriceListProduct.excluded_from_laptop.is_(False),
                ).order_by(PriceListProduct.preferred_price.asc()).limit(5)
            )
        ).scalars().all()

        discarded_samples = (
            await db.execute(
                select(PriceListProduct).where(
                    PriceListProduct.tenant_id == tid,
                    PriceListProduct.is_current.is_(True),
                    or_(
                        PriceListProduct.source_sheet.ilike("%warrant%"),
                        PriceListProduct.description.ilike("%keep your hd%"),
                    ),
                ).limit(10)
            )
        ).scalars().all()

    keep_in_laptop_search = any(
        r.product_type == "laptop" and not r.excluded_from_laptop for r in keep_hd_rows
    )

    lines = [
        "# Laptop Classification Audit",
        "",
        f"**Generado:** {now.isoformat()}",
        "",
        "## Totales",
        f"- Líneas con `product_type=laptop` (antes del filtro estricto): **{total_laptop_type}**",
        f"- Laptops válidas (`excluded_from_laptop=false`): **{true_laptops}**",
        f"- Excluidas de búsqueda laptop: **{excluded}**",
        "",
        "## Validación crítica: «1Y Keep Your HD»",
        f"- Filas encontradas: **{len(keep_hd_rows)}**",
        f"- ¿Aparece en búsqueda laptop?: **{'SÍ — FAIL' if keep_in_laptop_search else 'NO — OK'}**",
        "",
    ]
    for r in keep_hd_rows:
        lines.append(
            f"  - `{r.description}` | hoja={r.source_sheet} | tipo={r.product_type} | "
            f"excluido={r.excluded_from_laptop} | precio={r.preferred_price}"
        )

    lines.extend([
        "",
        "## Warranties clasificadas como laptop (debe ser 0)",
        f"- Count FAIL: **{len(warranty_as_laptop)}**",
        "",
        "## Ejemplos laptops válidas",
    ])
    for s in valid_samples:
        lines.append(
            f"- {s.description[:80] if s.description else s.sku} | "
            f"{s.source_sheet} fila {s.source_row} | {s.currency} {s.preferred_price}"
        )

    lines.extend(["", "## Ejemplos líneas descartadas/excluidas"])
    for s in discarded_samples:
        reason = s.classification_label or s.product_type
        if contains_non_laptop_keyword(s.description or ""):
            reason = "keyword no-laptop"
        lines.append(
            f"- {s.description[:80] if s.description else '—'} | hoja={s.source_sheet} | "
            f"tipo={s.product_type} | razón={reason}"
        )

    lines.extend([
        "",
        "## Hojas excluidas de comparación laptop",
        "- Warranties, Accesorios, Support, Services, Loc.ID, Alloc, etc.",
        "",
        "## Criterio PASS",
        "- «1Y Keep Your HD» NO en search?q=laptop",
        "- 0 warranties con excluded_from_laptop=false",
    ])

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report: {report_path}")
    return 1 if keep_in_laptop_search or warranty_as_laptop else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default=".qa/laptop-classification-audit.md")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(Path(args.report))))


if __name__ == "__main__":
    main()
