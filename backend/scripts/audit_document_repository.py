#!/usr/bin/env python3
"""Auditoría integral del repositorio documental JAIOS — BD vs archivos físicos."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select, text, update

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentAlert, DocumentChunk, DocumentRelationship
from app.models.knowledge import KnowledgeAsset, KnowledgeRelationship
from app.models.search_index import SearchIndexEntry
from app.models.tenant import Tenant

OFFICIAL_FOLDERS = frozenset(settings.knowledge_sync_folder_list)


def _file_hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


async def run_audit(*, tenant_slug: str, apply: bool, report_path: Path) -> dict:
    async with AsyncSessionLocal() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        ).scalar_one_or_none()
        if not tenant:
            raise SystemExit(f"Tenant no encontrado: {tenant_slug}")
        tid = tenant.id

        source_root = Path(settings.knowledge_source_path)
        docs_storage = Path(settings.documents_storage_path) / str(tid)

        # ── DB counts ──
        async def count(sql: str) -> int:
            return int((await session.execute(text(sql), {"tid": str(tid)})).scalar() or 0)

        db_counts = {
            "documents_all": await count(
                "SELECT COUNT(*) FROM jaios.documents WHERE tenant_id = :tid"
            ),
            "documents_active": await count(
                "SELECT COUNT(*) FROM jaios.documents WHERE tenant_id = :tid AND is_active"
            ),
            "documents_archived": await count(
                "SELECT COUNT(*) FROM jaios.documents WHERE tenant_id = :tid AND NOT is_active"
            ),
            "document_chunks": await count(
                "SELECT COUNT(*) FROM jaios.document_chunks WHERE tenant_id = :tid"
            ),
            "document_relationships": await count(
                "SELECT COUNT(*) FROM jaios.document_relationships WHERE tenant_id = :tid"
            ),
            "document_alerts": await count(
                "SELECT COUNT(*) FROM jaios.document_alerts WHERE tenant_id = :tid"
            ),
            "knowledge_active": await count(
                "SELECT COUNT(*) FROM jaios.knowledge_assets WHERE tenant_id = :tid AND is_active"
            ),
            "knowledge_archived": await count(
                "SELECT COUNT(*) FROM jaios.knowledge_assets WHERE tenant_id = :tid AND NOT is_active"
            ),
            "knowledge_relationships": await count(
                "SELECT COUNT(*) FROM jaios.knowledge_relationships WHERE tenant_id = :tid"
            ),
        }
        try:
            db_counts["search_index"] = await count(
                "SELECT COUNT(*) FROM jaios.search_index WHERE tenant_id = :tid"
            )
        except Exception:
            db_counts["search_index"] = None

        # ── Active documents audit ──
        active_docs = list(
            (
                await session.execute(
                    select(Document).where(
                        Document.tenant_id == tid,
                        Document.is_active.is_(True),
                    )
                )
            ).scalars().all()
        )

        missing_files: list[dict] = []
        bad_titles: list[dict] = []
        contaminated: list[dict] = []
        valid_docs: list[dict] = []
        dup_groups: dict[str, list[Document]] = defaultdict(list)

        for doc in active_docs:
            dup_groups[doc.filename].append(doc)
            path = Path(doc.storage_path) if doc.storage_path else None
            exists = path.is_file() if path else False
            is_contaminated = " — " in (doc.title or "") and any(
                t in (doc.title or "").upper()
                for t in ("MINERD", "DGCP", "CM-", "DAF-", "MESCYT")
            )
            is_bad_title = (doc.title or "").startswith("Título ")
            entry = {
                "id": str(doc.id),
                "title": doc.title,
                "filename": doc.filename,
                "storage_path": doc.storage_path,
                "file_exists": exists,
            }
            if is_contaminated:
                contaminated.append(entry)
            elif is_bad_title:
                bad_titles.append(entry)
            if not exists:
                missing_files.append(entry)
            elif not is_contaminated and not is_bad_title:
                valid_docs.append(entry)

        duplicates = {
            fn: [str(d.id) for d in docs]
            for fn, docs in dup_groups.items()
            if len(docs) > 1
        }

        # ── Physical files in official folders ──
        physical_by_folder: dict[str, int] = {}
        physical_files: list[str] = []
        if source_root.is_dir():
            for folder in sorted(OFFICIAL_FOLDERS):
                folder_path = source_root / folder
                if not folder_path.is_dir():
                    physical_by_folder[folder] = 0
                    continue
                files = [
                    p
                    for p in folder_path.rglob("*")
                    if p.is_file() and not p.name.startswith(".")
                ]
                physical_by_folder[folder] = len(files)
                for p in files:
                    physical_files.append(str(p.relative_to(source_root)).replace("\\", "/"))

        # ── Knowledge assets vs physical ──
        knowledge_active = list(
            (
                await session.execute(
                    select(KnowledgeAsset).where(
                        KnowledgeAsset.tenant_id == tid,
                        KnowledgeAsset.is_active.is_(True),
                    )
                )
            ).scalars().all()
        )
        knowledge_paths = {a.relative_path for a in knowledge_active}
        knowledge_missing_file: list[str] = []
        knowledge_orphan_db: list[str] = []
        for asset in knowledge_active:
            full = source_root / asset.relative_path
            if not full.is_file():
                knowledge_missing_file.append(asset.relative_path)
            if asset.folder_category not in OFFICIAL_FOLDERS:
                knowledge_orphan_db.append(asset.relative_path)

        physical_set = set(physical_files)
        files_without_db = sorted(physical_set - knowledge_paths)
        db_without_files = sorted(knowledge_paths - physical_set)

        repairs = {"archived": 0, "titles_fixed": 0, "deduped": 0}

        if apply:
            now = datetime.now(timezone.utc)
            # Archive missing, contaminated, bad-title test duplicates
            for doc in active_docs:
                path = Path(doc.storage_path) if doc.storage_path else None
                exists = path.is_file() if path else False
                should_archive = (
                    not exists
                    or (doc.title or "").startswith("Título ")
                    or (
                        " — " in (doc.title or "")
                        and any(
                            t in (doc.title or "").upper()
                            for t in ("MINERD", "DGCP", "CM-", "DAF-")
                        )
                    )
                    or doc.filename == "contrato_ademi.txt"
                )
                if should_archive:
                    doc.is_active = False
                    meta = dict(doc.metadata_ or {})
                    meta["archived_reason"] = "audit_orphan_or_test"
                    meta["archived_at"] = now.isoformat()
                    doc.metadata_ = meta
                    repairs["archived"] += 1
                elif (doc.title or "") != doc.filename:
                    doc.title = doc.filename
                    repairs["titles_fixed"] += 1

            # Dedupe remaining active by filename — keep newest with file
            remaining = list(
                (
                    await session.execute(
                        select(Document).where(
                            Document.tenant_id == tid,
                            Document.is_active.is_(True),
                        )
                    )
                ).scalars().all()
            )
            by_fn: dict[str, list[Document]] = defaultdict(list)
            for d in remaining:
                by_fn[d.filename].append(d)
            for fn, group in by_fn.items():
                if len(group) <= 1:
                    continue
                group.sort(key=lambda d: d.updated_at or d.created_at, reverse=True)
                for dup in group[1:]:
                    dup.is_active = False
                    meta = dict(dup.metadata_ or {})
                    meta["archived_reason"] = "audit_duplicate"
                    dup.metadata_ = meta
                    repairs["deduped"] += 1

            await session.commit()

        # Post-repair counts
        active_after = await count(
            "SELECT COUNT(*) FROM jaios.documents WHERE tenant_id = :tid AND is_active"
        )
        knowledge_after = await count(
            "SELECT COUNT(*) FROM jaios.knowledge_assets WHERE tenant_id = :tid AND is_active"
        )

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tenant": tenant_slug,
            "mode": "APPLIED" if apply else "DRY_RUN",
            "official_folders_config": sorted(OFFICIAL_FOLDERS),
            "source_root": str(source_root),
            "source_available": source_root.is_dir(),
            "documents_storage": str(docs_storage),
            "db_counts": db_counts,
            "physical_files_by_folder": physical_by_folder,
            "physical_files_total": sum(physical_by_folder.values()),
            "active_documents_audit": {
                "total_active": len(active_docs),
                "valid_corporate": len(valid_docs),
                "missing_file": len(missing_files),
                "bad_title_prefix": len(bad_titles),
                "contaminated_dgcp": len(contaminated),
                "duplicate_filename_groups": len(duplicates),
            },
            "knowledge_audit": {
                "active_in_db": len(knowledge_active),
                "missing_physical_file": len(knowledge_missing_file),
                "outside_official_folder": len(knowledge_orphan_db),
                "physical_not_indexed": len(files_without_db),
                "indexed_not_physical": len(db_without_files),
            },
            "samples": {
                "missing_files": missing_files[:10],
                "bad_titles": bad_titles[:10],
                "duplicates": dict(list(duplicates.items())[:5]),
                "files_without_db": files_without_db[:15],
            },
            "repairs": repairs if apply else None,
            "after_apply": {
                "documents_active": active_after,
                "knowledge_active": knowledge_after,
            }
            if apply
            else None,
            "root_causes": [
                "health() contaba documentos archivados (1381 = 1342 archivados + 39 activos)",
                "Tabla documents contenía fixtures de pytest duplicados (contrato_ademi.txt x21)",
                "Títulos de prueba con prefijo 'Título ' mezclados con filename real",
                "Repositorio corporativo real está en knowledge_assets sincronizado desde JustechAI",
            ],
            "recommendations": [
                "Usar knowledge sync como fuente corporativa (/knowledge/assets)",
                "health() debe contar solo activos con archivo físico válido",
                "Ejecutar POST /knowledge/sync tras reparación",
                "Chunks (21) son internos — no deben sumarse como documentos",
            ],
        }

        report_path.parent.mkdir(parents=True, exist_ok=True)
        md = _render_markdown(report)
        report_path.write_text(md, encoding="utf-8")
        report_path.with_suffix(".json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return report


def _render_markdown(r: dict) -> str:
    lines = [
        "# Auditoría repositorio documental JAIOS",
        "",
        f"- **Generado:** {r['generated_at']}",
        f"- **Tenant:** {r['tenant']}",
        f"- **Modo:** {r['mode']}",
        "",
        "## Conteos BD",
    ]
    for k, v in r["db_counts"].items():
        lines.append(f"- {k}: **{v}**")
    lines.extend([
        "",
        "## Archivos físicos (carpetas oficiales)",
        f"- Total físico indexable: **{r['physical_files_total']}**",
    ])
    for folder, n in sorted(r["physical_files_by_folder"].items()):
        lines.append(f"- {folder}: {n}")
    a = r["active_documents_audit"]
    lines.extend([
        "",
        "## Auditoría documents (activos)",
        f"- Activos: **{a['total_active']}**",
        f"- Válidos corporativos: **{a['valid_corporate']}**",
        f"- Sin archivo físico: **{a['missing_file']}**",
        f"- Título 'Título …' (test): **{a['bad_title_prefix']}**",
        f"- Contaminados DGCP: **{a['contaminated_dgcp']}**",
        f"- Grupos duplicados por filename: **{a['duplicate_filename_groups']}**",
        "",
        "## Auditoría knowledge_assets",
    ])
    k = r["knowledge_audit"]
    lines.extend([
        f"- Activos en BD: **{k['active_in_db']}**",
        f"- Sin archivo físico: **{k['missing_physical_file']}**",
        f"- Fuera de carpeta oficial: **{k['outside_official_folder']}**",
        f"- Físicos sin indexar: **{k['physical_not_indexed']}**",
        f"- Indexados sin físico: **{k['indexed_not_physical']}**",
        "",
        "## Causas raíz",
        *[f"- {c}" for c in r["root_causes"]],
        "",
        "## Recomendaciones",
        *[f"- {x}" for x in r["recommendations"]],
    ])
    if r.get("repairs"):
        lines.extend(["", "## Reparaciones aplicadas", f"```json\n{json.dumps(r['repairs'], indent=2)}\n```"])
    if r.get("after_apply"):
        lines.extend([
            "",
            "## Después de reparación",
            f"- documents activos: **{r['after_apply']['documents_active']}**",
            f"- knowledge activos: **{r['after_apply']['knowledge_active']}**",
        ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Auditoría repositorio documental")
    parser.add_argument("--tenant", default="justech")
    parser.add_argument("--apply", action="store_true", help="Archivar huérfanos/duplicados y corregir títulos")
    parser.add_argument(
        "--report",
        default=".qa/document-repository-audit.md",
    )
    args = parser.parse_args()
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = Path(__file__).resolve().parents[2] / report_path
    report = asyncio.run(run_audit(tenant_slug=args.tenant, apply=args.apply, report_path=report_path))
    print(json.dumps(report["active_documents_audit"], indent=2))
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
