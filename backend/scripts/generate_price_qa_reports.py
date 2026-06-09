#!/usr/bin/env python3
"""Genera reportes QA de Price Intelligence."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.price_list import PriceListProduct
from app.models.tenant import Tenant


async def _login(client: AsyncClient) -> dict | None:
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@justech.do", "password": "JaiosAdmin2026!", "tenant_slug": "justech"},
    )
    if r.status_code != 200:
        return None
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def run(qa_dir: Path) -> int:
    qa_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = await _login(client)
        if not headers:
            print("Login falló — reportes parciales", file=sys.stderr)

        search_laptop = search_spec = compare = assistant = odoo_match = quote_drafts = detail = None
        search_keep_hd = None
        detail_id = None
        if headers:
            search_laptop = await client.get("/api/v1/prices/search", params={"q": "laptop", "limit": 200}, headers=headers)
            search_keep_hd = await client.get(
                "/api/v1/prices/search",
                params={"q": "laptop", "limit": 200},
                headers=headers,
            )
            if search_laptop and search_laptop.status_code == 200:
                items = search_laptop.json().get("items", [])
                if items:
                    detail_id = items[0]["id"]
            search_spec = await client.get(
                "/api/v1/prices/search",
                params={"categoria": "laptop", "ram_gb": 16, "almacenamiento_gb": 512, "limit": 5},
                headers=headers,
            )
            compare = await client.get(
                "/api/v1/prices/compare",
                params={"categoria": "laptop", "ram_gb": 16, "almacenamiento_gb": 512},
                headers=headers,
            )
            assistant = await client.post(
                "/api/v1/assistant/query",
                json={"question": "¿Quién me sale mejor laptop 16GB 512GB?", "current_module": "/prices"},
                headers=headers,
            )
            quote_drafts = await client.get("/api/v1/prices/quote-drafts", headers=headers)
            if detail_id:
                detail = await client.get(f"/api/v1/prices/products/{detail_id}", headers=headers)
                odoo_match = await client.get(f"/api/v1/prices/products/{detail_id}/odoo-match", headers=headers)

    # price-search-validation.md
    sl = search_laptop.json() if search_laptop and search_laptop.status_code == 200 else {}
    ss = search_spec.json() if search_spec and search_spec.status_code == 200 else {}
    laptop_items = sl.get("items", [])
    keep_hd_in_laptop = [
        i for i in laptop_items
        if i.get("description") and "keep your hd" in i["description"].lower()
    ]
    (qa_dir / "price-search-validation.md").write_text(
        "\n".join([
            "# Price Search Validation",
            "",
            f"**Generado:** {now}",
            "",
            "## GET /api/v1/prices/search?q=laptop",
            f"- HTTP: {search_laptop.status_code if search_laptop else 'skip'}",
            f"- Total: **{sl.get('total', 0)}**",
            f"- «Keep Your HD» en resultados: **{len(keep_hd_in_laptop)}** ({'FAIL' if keep_hd_in_laptop else 'OK'})",
            "",
            "## GET /api/v1/prices/search?categoria=laptop&ram_gb=16&almacenamiento_gb=512",
            f"- HTTP: {search_spec.status_code if search_spec else 'skip'}",
            f"- Total: **{ss.get('total', 0)}**",
            "",
            "## Criterio",
            "- Solo laptops válidas (excluded_from_laptop=false)",
            "- Sin warranties/accesorios en búsqueda laptop",
            "- preferred_price = PRECIO FINAL en hojas Comercial/Laptop Local",
            "",
        ]) + "\n",
        encoding="utf-8",
    )

    cmp = compare.json() if compare and compare.status_code == 200 else {}
    best = cmp.get("best_product") or {}
    (qa_dir / "price-detail-validation.md").write_text(
        "\n".join([
            "# Price Detail Validation",
            "",
            f"**Generado:** {now}",
            "",
            f"## GET /api/v1/prices/products/{{id}}",
            f"- HTTP: {detail.status_code if detail else 'skip'}",
            f"- Producto muestra: `{detail_id}`",
            "",
            "## Compare laptop 16GB 512GB",
            f"- HTTP: {compare.status_code if compare else 'skip'}",
            f"- Mejor: {best.get('supplier')} — {best.get('currency')} {best.get('preferred_price') or best.get('price')}",
            f"- Fuente: {best.get('source_filename')} / {best.get('source_sheet')} fila {best.get('source_row')}",
            f"- Fecha lista: {best.get('source_file_date')}",
            "",
        ]) + "\n",
        encoding="utf-8",
    )

    aj = assistant.json() if assistant and assistant.status_code == 200 else {}
    (qa_dir / "price-assistant-validation.md").write_text(
        "\n".join([
            "# Price Assistant Validation",
            "",
            f"**Generado:** {now}",
            "",
            "## Pregunta: ¿Quién me sale mejor laptop 16GB 512GB?",
            f"- HTTP: {assistant.status_code if assistant else 'skip'}",
            f"- query_type: `{aj.get('query_type')}`",
            f"- sources: {aj.get('sources')}",
            "",
            "## Respuesta (extracto)",
            "",
            aj.get("answer", "—")[:800],
            "",
        ]) + "\n",
        encoding="utf-8",
    )

    qd = quote_drafts.json() if quote_drafts and quote_drafts.status_code == 200 else {}
    om = odoo_match.json() if odoo_match and odoo_match.status_code == 200 else {}
    (qa_dir / "price-quote-draft-validation.md").write_text(
        "\n".join([
            "# Price Quote Draft Validation",
            "",
            f"**Generado:** {now}",
            "",
            "## GET /api/v1/prices/quote-drafts",
            f"- HTTP: {quote_drafts.status_code if quote_drafts else 'skip'}",
            f"- Total borradores: **{qd.get('total', 0)}**",
            "",
            "## Flujo operativo",
            "- POST /prices/quote-drafts crea borrador + tarea ventas + notificación",
            "- Visible en /prices/drafts y /tasks",
            "",
        ]) + "\n",
        encoding="utf-8",
    )

    (qa_dir / "price-odoo-readiness.md").write_text(
        "\n".join([
            "# Price Odoo Readiness",
            "",
            f"**Generado:** {now}",
            "",
            f"## GET /api/v1/prices/products/{{id}}/odoo-match",
            f"- HTTP: {odoo_match.status_code if odoo_match else 'skip'}",
            f"- Encontrado: **{om.get('found')}**",
            f"- Acción: `{om.get('action', 'none')}`",
            f"- Mensaje: {om.get('message', '—')}",
            "",
            "## Política",
            "- No crear cotización/producto en Odoo automáticamente",
            "- Búsqueda controlada por SKU/MPN/modelo",
            "",
        ]) + "\n",
        encoding="utf-8",
    )

    (qa_dir / "price-final-qa.md").write_text(
        "\n".join([
            "# Price Intelligence — QA Final",
            "",
            f"**Generado:** {now}",
            "",
            "## Estado",
            "**VALIDACIÓN FALLIDA** hasta revisión visual de Fausto.",
            "",
            "## Checks automáticos",
            f"- Laptops search total: {sl.get('total', 0)}",
            f"- Keep Your HD en laptop search: {len(keep_hd_in_laptop)} ({'FAIL' if keep_hd_in_laptop else 'OK'})",
            f"- Compare 16GB/512GB: {best.get('supplier', '—')} {best.get('preferred_price', '—')}",
            f"- Quote drafts API: HTTP {quote_drafts.status_code if quote_drafts else 'skip'}",
            "",
            "## Pendiente Fausto",
            "- Confirmar precios vs Excel fila a fila",
            "- Confirmar stock vs Excel",
            "- Probar preparar cotización → borrador → tarea",
            "",
        ]) + "\n",
        encoding="utf-8",
    )

    print(f"QA reports written to {qa_dir}")
    return 0


def main() -> None:
    qa_dir = Path.cwd() / ".qa"
    raise SystemExit(asyncio.run(run(qa_dir)))


if __name__ == "__main__":
    main()
