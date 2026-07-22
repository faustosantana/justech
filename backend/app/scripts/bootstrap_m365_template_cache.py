"""Descarga y cachea TODAS las plantillas DOCX oficiales indexadas en M365."""

from __future__ import annotations

import asyncio
import sys

import httpx
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.m365_repository import M365RepositoryFile
from app.models.tenant import Tenant
from app.models.user import User
from app.scripts.seed import ADMIN_EMAIL
from app.services.document_autofill.m365_template_cache import read_cached_bytes, write_cached_bytes
from app.services.document_autofill.m365_template_catalog import is_dgcp_template_candidate
from app.services.document_autofill.m365_template_resolver import M365TemplateReference, M365TemplateResolver

DGCP_BASE = "https://www.dgcp.gob.do/new_dgcp/documentos/politicas_normas_y_procedimientos/documentos_estandar/escudo"


async def _download_dgcp_by_name(name: str) -> bytes | None:
    """Descarga plantilla oficial DGCP por nombre de archivo."""
    fname = name.strip()
    if not fname.lower().endswith(".docx"):
        return None
    url = f"{DGCP_BASE}/{fname}"
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        resp = await client.get(url)
        if resp.status_code == 200 and len(resp.content) > 1000:
            return resp.content
    # Variantes de nombre (espacios, guiones)
    alt = fname.replace(" ", "_")
    if alt != fname:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(f"{DGCP_BASE}/{alt}")
            if resp.status_code == 200 and len(resp.content) > 1000:
                return resp.content
    return None


async def main() -> int:
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).where(Tenant.slug == "justech"))).scalar_one()
        admin = (
            await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one_or_none()
        user_id = admin.id if admin else None
        resolver = M365TemplateResolver(db, tenant.id, user_id=user_id)

        rows = (
            await db.execute(
                select(M365RepositoryFile).where(
                    M365RepositoryFile.tenant_id == tenant.id,
                    M365RepositoryFile.is_deleted.is_(False),
                    M365RepositoryFile.is_folder.is_(False),
                )
            )
        ).scalars().all()

        candidates = [r for r in rows if is_dgcp_template_candidate(r)]
        docx_rows = [r for r in candidates if (r.name or "").lower().endswith(".docx")]

        ok = 0
        fail = 0
        skip = 0
        for row in sorted(docx_rows, key=lambda r: r.name.lower()):
            if read_cached_bytes(row.id):
                skip += 1
                continue
            ref = M365TemplateReference(
                form_type="",
                m365_file_id=row.id,
                graph_item_id=row.graph_item_id,
                drive_id=row.drive_id,
                source=row.source,
                name=row.name,
                web_url=row.web_url,
                parent_path=row.parent_path,
                content_hash=row.content_hash,
                template_version=row.content_hash or "index",
                document_type=row.document_type,
                resolver="m365_index",
            )
            try:
                content = await resolver.download_bytes(ref)
            except Exception:
                content = await _download_dgcp_by_name(row.name)
                if not content:
                    print(f"FAIL {row.name}", file=sys.stderr)
                    fail += 1
                    continue
            write_cached_bytes(row.id, content)
            print(f"OK {row.name} ({len(content)} bytes)")
            ok += 1

        print(f"\nResumen: {ok} cacheadas, {skip} ya en caché, {fail} fallidas, {len(docx_rows)} DOCX indexados")
        return 0 if fail == 0 else 2 if ok + skip > 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
