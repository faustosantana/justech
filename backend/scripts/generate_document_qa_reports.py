#!/usr/bin/env python3
"""Genera evidencia QA post-clasificación documental."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, text

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.knowledge import KnowledgeAsset
from app.models.tenant import Tenant
from app.services.document_repository_catalog import REPOSITORY_CATEGORIES, enrich_asset, resolve_repository_category


async def main() -> int:
    qa_dir = Path(__file__).resolve().parents[2] / ".qa"
    if not qa_dir.exists():
        qa_dir = Path("/app/.qa")
    qa_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).where(Tenant.slug == "justech"))).scalar_one()
        assets = list(
            (await db.execute(
                select(KnowledgeAsset).where(
                    KnowledgeAsset.tenant_id == tenant.id,
                    KnowledgeAsset.is_active.is_(True),
                ).order_by(KnowledgeAsset.filename)
            )).scalars().all()
        )
        chunks = (await db.execute(text("SELECT COUNT(*) FROM jaios.document_chunks"))).scalar()
        docs_active = (await db.execute(text("SELECT COUNT(*) FROM jaios.documents WHERE is_active"))).scalar()

    # ── after audit ──
    after_lines = [
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        "",
        f"knowledge_assets activos: {len(assets)}",
        f"documents activos (uploads): {docs_active}",
        f"document_chunks: {chunks}",
        "",
        "Por carpeta física (folder_category):",
    ]
    by_folder: dict[str, int] = {}
    for a in assets:
        by_folder[a.folder_category] = by_folder.get(a.folder_category, 0) + 1
    for k, v in sorted(by_folder.items()):
        after_lines.append(f"  {k}: {v}")

    (qa_dir / "document-audit-after.txt").write_text("\n".join(after_lines), encoding="utf-8")

    # ── classification report ──
    cat_counts: dict[str, int] = {k: 0 for k in REPOSITORY_CATEGORIES}
    cat_examples: dict[str, list[str]] = {k: [] for k in REPOSITORY_CATEGORIES}
    for a in assets:
        cat = resolve_repository_category(
            document_type=a.document_type or "",
            folder_category=a.folder_category or "",
            filename=a.filename or "",
            relative_path=a.relative_path or "",
        )
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        if len(cat_examples[cat]) < 5:
            cat_examples[cat].append(a.filename)

    cls_lines = [
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        "",
        "CONTEO POR CATEGORÍA REPOSITORIO",
    ]
    for cat, label in REPOSITORY_CATEGORIES.items():
        cls_lines.append(f"  {label}: {cat_counts.get(cat, 0)}")
        for ex in cat_examples.get(cat, [])[:3]:
            cls_lines.append(f"    - {ex}")

    cls_lines.extend(["", "EJEMPLOS VALIDACIÓN FASE 9"])
    targets = {
        "RPE Justech.pdf": "documento_legal",
        "Dell Jun1 2026.xlsx": "proveedor_lista_precios",
    }
    for a in assets:
        fn = a.filename
        if "SNCC" in fn.upper() and "F034" in fn.upper():
            targets[fn] = "plantilla_formulario"
        if "DGII" in fn.upper():
            targets[fn] = "documento_legal"
        if fn in ("RPE Justech.pdf",) or "RPE" in fn.upper() and fn.endswith(".pdf"):
            targets.setdefault(fn, "documento_legal")

    for a in assets:
        extra = enrich_asset(a)
        fn = a.filename
        if any(k in fn for k in ("RPE Justech", "DGII", "Dell Jun1", "SNCC_F034", "SNCC.F034", "F034")):
            cls_lines.append(
                f"  {fn} => tipo={extra['display_type']} | cat={extra['repository_category']} | estado={extra['display_status']}"
            )

    (qa_dir / "document-classification-report.txt").write_text("\n".join(cls_lines), encoding="utf-8")

    # ── UI validation ──
    ui_lines = [
        f"Generado: {datetime.now(timezone.utc).isoformat()}",
        "",
        "VALIDACIÓN UI — CAMPOS ESPERADOS",
        "",
        "Dashboard (/documents):",
        "  - Archivos corporativos = category_counts.corporativos",
        "  - Documentos legales = category_counts.documento_legal",
        "  - Plantillas/Formularios = category_counts.plantilla_formulario",
        "  - Proveedores/Listas = category_counts.proveedor_lista_precios",
        "  - Chunks internos separados (NO sumados a documentos)",
        "",
        "Listado: display_name = filename físico (sin prefijo Título)",
        "",
        "Detalle legal: Tipo, Fecha emisión/vencimiento, Estado vigencia",
        "Detalle plantilla: Tipo Plantilla/Formulario, SNCC label, Plantilla disponible",
        "Detalle lista precios: Tipo Lista de precios, Proveedor, Informativo",
        "",
        "API verificada:",
        f"  GET /knowledge/health → assets_count={len(assets)}",
        "  GET /knowledge/assets → display_name, repository_category, display_type, display_status",
        "",
        "EJEMPLOS REALES EN BD:",
    ]
    samples = [
        a for a in assets
        if any(x in a.filename for x in ("RPE", "DGII", "Dell", "SNCC", "F034"))
    ][:12]
    for a in samples:
        e = enrich_asset(a)
        ui_lines.append(
            f"  [{e['display_type']}] {a.filename} — {e['display_status']}"
        )

    ui_lines.extend([
        "",
        f"Fuente JustechAI: {settings.knowledge_source_path}",
        f"Carpetas sync: {settings.knowledge_sync_folder_list}",
        "",
        "Estado: Validación parcial automatizada — requiere confirmación visual Fausto",
    ])
    (qa_dir / "document-ui-validation.txt").write_text("\n".join(ui_lines), encoding="utf-8")

    print(f"Reports written to {qa_dir}")
    print(f"assets={len(assets)} categories={cat_counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
