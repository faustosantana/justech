"""Descarga plantillas oficiales DGCP por nombre de archivo — independiente de OAuth."""

from __future__ import annotations

import httpx

DGCP_BASE = (
    "https://www.dgcp.gob.do/new_dgcp/documentos/politicas_normas_y_procedimientos/documentos_estandar/escudo"
)


async def download_dgcp_official_docx(filename: str) -> bytes | None:
    fname = (filename or "").strip()
    if not fname.lower().endswith(".docx"):
        return None
    candidates = [fname, fname.replace(" ", "_")]
    seen: set[str] = set()
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            resp = await client.get(f"{DGCP_BASE}/{candidate}")
            if resp.status_code == 200 and len(resp.content) > 1000:
                return resp.content
    return None
