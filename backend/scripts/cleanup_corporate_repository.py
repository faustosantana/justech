#!/usr/bin/env python3
"""Limpieza segura del repositorio corporativo — solo BD/índices, sin borrar archivos físicos."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, func, or_, select, update

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentAlert, DocumentChunk, DocumentRelationship
from app.models.knowledge import KnowledgeAlert, KnowledgeAsset, KnowledgeRelationship
from app.models.search_index import SearchIndexEntry
from app.models.tenant import Tenant

OFFICIAL_KNOWLEDGE_FOLDERS = frozenset({
    "00_DATOS_EMPRESAS",
    "01_DOCUMENTOS_LEGALES",
    "02_PLANTILLAS",
    "03_PROVEEDORES",
    "04_FICHAS_TECNICAS",
    "05_COTIZACIONES",
})

DGCP_TITLE_COPY = re.compile(r"^[A-Z0-9][A-Z0-9._-]{4,}\s+—\s+", re.IGNORECASE)
CONTAMINATED_METADATA_KEYS = ("dgcp", "knowledge_copy", "process_copy", "dgcp_process")


def _is_contaminated_document(doc: Document) -> tuple[bool, str]:
    meta = doc.metadata_ or {}
    meta_blob = json.dumps(meta, ensure_ascii=False).lower()
    if any(k in meta_blob for k in CONTAMINATED_METADATA_KEYS):
        return True, "metadata_dgcp_or_copy"
    if DGCP_TITLE_COPY.match(doc.title or ""):
        return True, "dgcp_title_prefix"
    if " — " in (doc.title or "") and any(
        token in (doc.title or "").upper()
        for token in ("MINERD", "MESCYT", "INABIMA", "DGCP", "LPN-", "CM-", "DAF-")
    ):
        return True, "process_code_in_title"
    tags = " ".join(doc.tags or []).lower()
    if "knowledge_copy" in tags or "dgcp" in tags:
        return True, "tags_contamination"
    return False, ""


def _is_contaminated_knowledge(asset: KnowledgeAsset) -> tuple[bool, str]:
    if asset.folder_category not in OFFICIAL_KNOWLEDGE_FOLDERS:
        return True, f"folder_{asset.folder_category}"
    rel = (asset.relative_path or "").upper()
    if rel.startswith("DGCP/") or "/DGCP/" in rel:
        return True, "path_dgcp"
    return False, ""


async def run_cleanup(*, tenant_slug: str, dry_run: bool, report_path: Path) -> dict:
    async with AsyncSessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        ).scalar_one_or_none()
        if not tenant:
            raise SystemExit(f"Tenant no encontrado: {tenant_slug}")

        tid = tenant.id

        docs_before = await session.scalar(
            select(func.count()).select_from(Document).where(
                Document.tenant_id == tid, Document.is_active.is_(True)
            )
        )
        knowledge_before = await session.scalar(
            select(func.count()).select_from(KnowledgeAsset).where(
                KnowledgeAsset.tenant_id == tid, KnowledgeAsset.is_active.is_(True)
            )
        )

        all_docs = (
            await session.execute(
                select(Document).where(Document.tenant_id == tid, Document.is_active.is_(True))
            )
        ).scalars().all()
        all_knowledge = (
            await session.execute(
                select(KnowledgeAsset).where(
                    KnowledgeAsset.tenant_id == tid, KnowledgeAsset.is_active.is_(True)
                )
            )
        ).scalars().all()

        doc_archive: list[dict] = []
        doc_keep: list[dict] = []
        doc_reasons: Counter[str] = Counter()

        for doc in all_docs:
            bad, reason = _is_contaminated_document(doc)
            row = {"id": str(doc.id), "title": doc.title, "category": doc.category}
            if bad:
                doc_archive.append({**row, "reason": reason})
                doc_reasons[reason] += 1
            else:
                doc_keep.append(row)

        knowledge_archive: list[dict] = []
        knowledge_keep: list[dict] = []
        knowledge_by_folder: Counter[str] = Counter()
        knowledge_reasons: Counter[str] = Counter()

        for asset in all_knowledge:
            bad, reason = _is_contaminated_knowledge(asset)
            row = {
                "id": str(asset.id),
                "title": asset.title,
                "folder": asset.folder_category,
                "path": asset.relative_path,
            }
            if bad:
                knowledge_archive.append({**row, "reason": reason})
                knowledge_reasons[reason] += 1
            else:
                knowledge_keep.append(row)
                knowledge_by_folder[asset.folder_category] += 1

        archive_doc_ids = [uuid.UUID(d["id"]) for d in doc_archive]
        archive_knowledge_ids = [uuid.UUID(k["id"]) for k in knowledge_archive]

        if not dry_run:
            if archive_doc_ids:
                await session.execute(
                    update(Document)
                    .where(Document.id.in_(archive_doc_ids))
                    .values(is_active=False)
                )
                await session.execute(
                    delete(DocumentChunk).where(DocumentChunk.document_id.in_(archive_doc_ids))
                )
                await session.execute(
                    delete(DocumentRelationship).where(
                        DocumentRelationship.document_id.in_(archive_doc_ids)
                    )
                )
                await session.execute(
                    update(DocumentAlert)
                    .where(DocumentAlert.document_id.in_(archive_doc_ids))
                    .values(is_resolved=True)
                )
                await session.execute(
                    update(SearchIndexEntry)
                    .where(
                        SearchIndexEntry.tenant_id == tid,
                        SearchIndexEntry.source == "documents",
                        SearchIndexEntry.entity_id.in_([str(i) for i in archive_doc_ids]),
                    )
                    .values(is_active=False)
                )

            if archive_knowledge_ids:
                await session.execute(
                    update(KnowledgeAsset)
                    .where(KnowledgeAsset.id.in_(archive_knowledge_ids))
                    .values(is_active=False)
                )
                await session.execute(
                    delete(KnowledgeRelationship).where(
                        KnowledgeRelationship.knowledge_asset_id.in_(archive_knowledge_ids)
                    )
                )
                await session.execute(
                    update(KnowledgeAlert)
                    .where(KnowledgeAlert.knowledge_asset_id.in_(archive_knowledge_ids))
                    .values(is_resolved=True)
                )
                await session.execute(
                    update(SearchIndexEntry)
                    .where(
                        SearchIndexEntry.tenant_id == tid,
                        SearchIndexEntry.source == "knowledge",
                        SearchIndexEntry.entity_id.in_([str(i) for i in archive_knowledge_ids]),
                    )
                    .values(is_active=False)
                )

            await session.commit()

        docs_after = docs_before - len(doc_archive) if not dry_run else len(doc_keep)
        knowledge_after = knowledge_before - len(knowledge_archive) if not dry_run else len(knowledge_keep)

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tenant_slug": tenant_slug,
            "dry_run": dry_run,
            "official_folders": sorted(OFFICIAL_KNOWLEDGE_FOLDERS),
            "documents": {
                "before": int(docs_before or 0),
                "after": int(docs_after),
                "archived": len(doc_archive),
                "kept": len(doc_keep),
                "archive_reasons": dict(doc_reasons),
                "kept_sample": doc_keep[:15],
            },
            "knowledge_assets": {
                "before": int(knowledge_before or 0),
                "after": int(knowledge_after),
                "archived": len(knowledge_archive),
                "kept": len(knowledge_keep),
                "kept_by_folder": dict(knowledge_by_folder),
                "archive_reasons": dict(knowledge_reasons),
            },
            "note": "Archivos físicos en disco NO eliminados — solo registros BD/índices.",
        }

        report_path.parent.mkdir(parents=True, exist_ok=True)
        md_lines = [
            "# Repository cleanup report",
            "",
            f"- **Generated:** {report['generated_at']}",
            f"- **Tenant:** {tenant_slug}",
            f"- **Mode:** {'DRY RUN' if dry_run else 'APPLIED'}",
            "",
            "## Documents (JAIOS documents table)",
            f"- Before: **{report['documents']['before']}**",
            f"- After: **{report['documents']['after']}**",
            f"- Archived: **{report['documents']['archived']}**",
            f"- Kept: **{report['documents']['kept']}**",
            "",
            "### Archive reasons",
            *[f"- {k}: {v}" for k, v in doc_reasons.items()],
            "",
            "## Knowledge assets (Corporate Repository)",
            f"- Before: **{report['knowledge_assets']['before']}**",
            f"- After: **{report['knowledge_assets']['after']}**",
            f"- Archived: **{report['knowledge_assets']['archived']}**",
            "",
            "### Kept by folder",
            *[f"- {k}: {v}" for k, v in sorted(knowledge_by_folder.items())],
            "",
            "## Root cause",
            "Copias DGCP (`{CODIGO} — {documento}`) indexadas en `documents` durante análisis previos.",
            "Knowledge assets ya limitados a carpetas oficiales; contaminación principal en `documents`.",
        ]
        report_path.write_text("\n".join(md_lines), encoding="utf-8")
        json_path = report_path.with_suffix(".json")
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup corporate repository indices")
    parser.add_argument("--tenant", default="justech")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--report",
        default=".qa/repository-cleanup-report.md",
        help="Markdown report path (relative to repo root or absolute)",
    )
    args = parser.parse_args()
    if not args.dry_run and not args.apply:
        print("Use --dry-run or --apply")
        return 1

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = Path(__file__).resolve().parents[2] / report_path

    report = asyncio.run(run_cleanup(tenant_slug=args.tenant, dry_run=args.dry_run, report_path=report_path))
    print(json.dumps(report["documents"], indent=2))
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
