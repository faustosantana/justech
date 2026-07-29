"""Format user-facing workspace table replies (no Huawei)."""

from __future__ import annotations

from app.lottery.ai.investigation_workspace.schemas import InvestigationAsset


def format_table_reply(
    asset: InvestigationAsset,
    *,
    intro: str | None = None,
) -> str:
    page_rows = asset.view_page()
    filt = asset.filters.model_dump(exclude_none=True)
    sort = asset.sort.model_dump()
    page = asset.pagination.page
    pages = max(
        1,
        (asset.row_count + asset.pagination.page_size - 1)
        // max(1, asset.pagination.page_size),
    )
    lines: list[str] = []
    if intro:
        lines.append(intro)
    else:
        lines.append(
            f"Encontré {asset.row_count} coincidencia(s). "
            f"Te muestro la tabla (página {page}/{pages}, "
            f"{len(page_rows)} fila(s) visibles)."
        )
    if filt:
        lines.append(f"Filtros activos: {filt}.")
    lines.append(f"Orden: {sort.get('field')} {sort.get('direction')}.")
    lines.append("")
    # Markdown-ish table
    cols = list(asset.columns)
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("| " + " | ".join("---" for _ in cols) + " |")
    for r in page_rows:
        lines.append("| " + " | ".join(str(r.get(c, "") or "") for c in cols) + " |")
    if not page_rows:
        lines.append("_(sin filas para los filtros actuales)_")
    lines.append("")
    lines.append(
        "Controles: Ver tabla · Filtrar · Ordenar · Exportar Excel · Ver resumen · Ver más"
    )
    if asset.download_url:
        lines.append(f"Descarga Excel: {asset.download_url}")
    return "\n".join(lines)


def format_export_reply(asset: InvestigationAsset) -> str:
    name = asset.export_filename or "export.xlsx"
    url = asset.download_url or ""
    return (
        f"Exportación lista: **{name}** ({asset.row_count} fila(s)).\n\n"
        f"Filtros: {asset.filters.model_dump(exclude_none=True) or 'ninguno'}.\n"
        f"Orden: {asset.sort.model_dump()}.\n\n"
        f"Descarga: {url}"
    )
