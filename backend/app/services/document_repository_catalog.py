"""Catálogo de clasificación del repositorio corporativo — sin tablas nuevas."""

from __future__ import annotations

import re
from datetime import date

from app.models.knowledge import KnowledgeAsset

# Categorías visibles en dashboard / UI
REPOSITORY_CATEGORIES: dict[str, str] = {
    "documento_legal": "Documentos legales",
    "datos_empresa": "Datos de empresa",
    "plantilla_formulario": "Plantillas/Formularios",
    "proveedor_lista_precios": "Proveedores/Listas",
    "clientes_cotizaciones": "Clientes/Cotizaciones",
    "ficha_tecnica": "Fichas técnicas",
}

LEGAL_DOCUMENT_TYPES = frozenset({
    "rpe",
    "rnc",
    "dgii",
    "tss",
    "registro_mercantil",
    "mipymes",
    "estatutos",
    "acta",
    "poder",
    "cedula",
    "certificacion_bancaria",
})

TEMPLATE_DOCUMENT_TYPES = frozenset({
    "formulario_sncc",
    "sncc_f033",
    "sncc_f034",
    "sncc_f042",
    "sncc_f047",
    "sncc_d040",
    "plantilla",
})

SNCC_FILENAME_RE = re.compile(r"sncc[_\.\-]?([a-z]?\d{2,3})", re.IGNORECASE)


def resolve_repository_category(
    *,
    document_type: str,
    folder_category: str,
    filename: str,
    relative_path: str = "",
) -> str:
    folder = (folder_category or "").upper()
    blob = f"{relative_path} {filename} {document_type}".lower()

    if folder.startswith("00_") or document_type == "datos_empresa":
        return "datos_empresa"
    if folder.startswith("04_FICHAS") or document_type == "ficha_tecnica":
        return "ficha_tecnica"
    if folder.startswith("05_") or document_type in ("lista_precios", "oferta_economica", "cotizacion"):
        if folder.startswith("03_"):
            return "proveedor_lista_precios"
        return "clientes_cotizaciones"
    if (
        folder.startswith("02_")
        or document_type in TEMPLATE_DOCUMENT_TYPES
        or "sncc" in blob
        or SNCC_FILENAME_RE.search(filename)
    ):
        return "plantilla_formulario"
    if (
        folder.startswith("03_")
        or document_type == "lista_precios"
        or any(k in blob for k in ("dell", "lenovo", "ingram", "hp ", "precio", "stock", "inventario"))
    ):
        return "proveedor_lista_precios"
    if document_type in LEGAL_DOCUMENT_TYPES or folder.startswith("01_"):
        return "documento_legal"
    return "documento_legal" if folder.startswith("01_") else "datos_empresa"


def resolve_display_type(repository_category: str) -> str:
    return {
        "documento_legal": "Documento legal",
        "datos_empresa": "Datos de empresa",
        "plantilla_formulario": "Plantilla/Formulario",
        "proveedor_lista_precios": "Lista de precios",
        "clientes_cotizaciones": "Cotización",
        "ficha_tecnica": "Ficha técnica",
    }.get(repository_category, "Documento corporativo")


def resolve_sncc_label(filename: str) -> str | None:
    m = SNCC_FILENAME_RE.search(filename)
    if not m:
        return None
    code = m.group(1).upper().replace(".", "")
    if code.startswith("F") or code.startswith("D") or code.startswith("P"):
        return f"SNCC {code}"
    return f"SNCC {code}"


def resolve_display_status(
    *,
    repository_category: str,
    vigency_status: str,
    valid_until: date | None,
) -> str:
    if repository_category == "plantilla_formulario":
        return "Plantilla disponible"
    if repository_category == "proveedor_lista_precios":
        return "Informativo"
    if repository_category == "datos_empresa":
        return "Referencia"
    if repository_category == "clientes_cotizaciones":
        return "Informativo"
    if repository_category == "ficha_tecnica":
        return "Referencia técnica"
    # Documento legal
    mapping = {
        "vigente": "Vigente",
        "proximo_a_vencer": "Próximo a vencer",
        "vencido": "Vencido",
        "sin_fecha": "Requiere revisión",
    }
    return mapping.get(vigency_status, "Requiere revisión")


def enrich_asset(asset: KnowledgeAsset) -> dict:
    """Campos derivados para API/UI — filename siempre como nombre visible."""
    repo_cat = resolve_repository_category(
        document_type=asset.document_type or "general",
        folder_category=asset.folder_category or "",
        filename=asset.filename or "",
        relative_path=asset.relative_path or "",
    )
    display_type = resolve_display_type(repo_cat)
    display_status = resolve_display_status(
        repository_category=repo_cat,
        vigency_status=asset.vigency_status or "sin_fecha",
        valid_until=asset.valid_until,
    )
    sncc_label = resolve_sncc_label(asset.filename) if repo_cat == "plantilla_formulario" else None
    supplier = asset.supplier_name or asset.manufacturer_name
    if repo_cat == "proveedor_lista_precios" and not supplier:
        name = asset.filename.lower()
        for brand in ("dell", "lenovo", "ingram", "hp", "samsung"):
            if brand in name:
                supplier = brand.title()
                break
    return {
        "display_name": asset.filename,
        "repository_category": repo_cat,
        "repository_category_label": REPOSITORY_CATEGORIES.get(repo_cat, repo_cat),
        "display_type": display_type,
        "display_status": display_status,
        "sncc_label": sncc_label,
        "detected_supplier": supplier,
        "requires_vigency": repo_cat == "documento_legal",
    }


def count_by_category(assets: list[KnowledgeAsset]) -> dict[str, int]:
    counts = {k: 0 for k in REPOSITORY_CATEGORIES}
    for asset in assets:
        cat = resolve_repository_category(
            document_type=asset.document_type or "general",
            folder_category=asset.folder_category or "",
            filename=asset.filename or "",
            relative_path=asset.relative_path or "",
        )
        counts[cat] = counts.get(cat, 0) + 1
    counts["corporativos"] = len(assets)
    return counts
