"""Catálogo y clasificación de plantillas M365 DGCP — todas las plantillas corporativas."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from app.models.m365_repository import M365RepositoryFile

# Carpetas / paths que identifican plantillas DGCP
DGCP_PATH_HINTS = (
    "plantilla",
    "dgcp",
    "02_plantillas",
    "proveedores_del_estado",
    "licitacion",
)

TEMPLATE_CATEGORIES = (
    "sncc_formulario",
    "sncc_documento",
    "sncc_pliego",
    "carta",
    "declaracion",
    "oferta_tecnica",
    "oferta_economica",
    "administrativo",
    "legal_reutilizable",
    "contrato",
    "portada",
    "consultoria",
    "proveedor",
    "datos_empresa",
    "general_dgcp",
)

SNCC_FORM_RE = re.compile(
    r"sncc[_\.\-\s]*(?:f|form)[_\.\-\s]*0*(\d{2,3})",
    re.I,
)
SNCC_DOC_RE = re.compile(r"sncc[_\.\-\s]*d[_\.\-\s]*0*(\d{2,3})", re.I)
SNCC_PLIEGO_RE = re.compile(r"sncc[_\.\-\s]*p[\.\-_]?0*(\d{2,3})", re.I)
SNCC_PROV_RE = re.compile(r"snccp?[_\.\-\s]*prov[_\.\-\s]*f[_\.\-\s]*0*(\d{2,3})", re.I)

EXCLUDE_NAME_RE = re.compile(
    r"(_copia|_final|autollenado|relleno|filled|preview|borrador|draft|~\$)",
    re.I,
)

DOCX_EXT = (".docx",)
PDF_EXT = (".pdf",)


@dataclass
class TemplateCatalogEntry:
    template_key: str
    form_type: str
    name: str
    m365_file_id: uuid.UUID
    graph_item_id: str
    drive_id: str | None
    source: str
    parent_path: str
    web_url: str | None
    document_type: str
    document_category: str
    detected_category: str
    detected_label: str
    format: str
    content_hash: str | None = None
    score: int = 0
    tags: list[str] = field(default_factory=list)

    def display_label(self) -> str:
        return self.detected_label or self.name.replace(".docx", "").replace("_", " ")


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip()).strip("-").lower()
    return s[:80] or "plantilla"


def _form_type_from_name(name: str) -> str:
    """Genera clave form_type estable desde nombre de archivo."""
    base = name.rsplit(".", 1)[0]
    m = SNCC_FORM_RE.search(base)
    if m:
        return f"SNCC.F{int(m.group(1)):03d}"
    m = SNCC_DOC_RE.search(base)
    if m:
        return f"SNCC.D{int(m.group(1)):03d}"
    m = SNCC_PLIEGO_RE.search(base)
    if m:
        return f"SNCC.P{int(m.group(1)):03d}"
    m = SNCC_PROV_RE.search(base)
    if m:
        return f"SNCCP.PROV.F{int(m.group(1)):03d}"
    if re.search(r"carta", base, re.I):
        return "CARTA." + _slugify(base).upper().replace("-", "_")[:40]
    if re.search(r"oferta.*econom", base, re.I):
        return "OFERTA.ECONOMICA"
    if re.search(r"oferta.*tecnic", base, re.I):
        return "OFERTA.TECNICA"
    if re.search(r"declar", base, re.I):
        return "DECLARACION." + _slugify(base).upper().replace("-", "_")[:30]
    return "PLANTILLA." + _slugify(base).upper().replace("-", "_")[:50]


def classify_template(name: str, parent_path: str = "", document_type: str = "") -> tuple[str, str, list[str]]:
    """Retorna (category, label, tags)."""
    blob = f"{parent_path} {name} {document_type}".lower()
    tags: list[str] = []

    if SNCC_FORM_RE.search(name):
        m = SNCC_FORM_RE.search(name)
        num = int(m.group(1)) if m else 0
        tags.append(f"sncc_f{num:03d}")
        if num in (33, 34):
            return "oferta_economica" if "econom" in blob else "sncc_formulario", f"SNCC F.{num:03d}", tags
        if num == 35:
            return "oferta_tecnica", "SNCC F.035 Soporte técnico", tags
        return "sncc_formulario", f"SNCC F.{num:03d}", tags

    if SNCC_DOC_RE.search(name):
        m = SNCC_DOC_RE.search(name)
        num = int(m.group(1)) if m else 0
        tags.append(f"sncc_d{num:03d}")
        if "carta" in blob:
            return "carta", f"SNCC D.{num:03d} Carta", tags
        if "contrato" in blob or document_type == "contrato":
            return "contrato", f"SNCC D.{num:03d} Contrato", tags
        if "experiencia" in blob or "curriculo" in blob or "metodologia" in blob:
            return "consultoria", f"SNCC D.{num:03d}", tags
        return "sncc_documento", f"SNCC D.{num:03d}", tags

    if SNCC_PLIEGO_RE.search(name) or "pliego" in blob:
        return "sncc_pliego", "Pliego SNCC", tags + ["pliego"]

    if SNCC_PROV_RE.search(name) or "debida diligencia" in blob:
        return "proveedor", "Formulario proveedor SNCCP", tags + ["proveedor"]

    if "carta" in blob:
        return "carta", "Carta", tags + ["carta"]
    if "oferta" in blob and "econom" in blob:
        return "oferta_economica", "Oferta económica", tags
    if "oferta" in blob and "tecnic" in blob:
        return "oferta_tecnica", "Oferta técnica", tags
    if "declar" in blob:
        return "declaracion", "Declaración", tags
    if "portada" in blob:
        return "portada", "Portada expediente", tags
    if document_type in ("carta",):
        return "carta", name.rsplit(".", 1)[0], tags
    if document_type in ("contrato",):
        return "contrato", name.rsplit(".", 1)[0], tags
    if "datos" in blob and "llenado" in blob:
        return "datos_empresa", "Datos para llenado", tags
    if parent_path and "01_documentos" in blob:
        return "legal_reutilizable", name.rsplit(".", 1)[0], tags + ["legal"]
    if "dgcp" in blob or "sncc" in blob:
        return "general_dgcp", name.rsplit(".", 1)[0], tags + ["dgcp"]
    return "administrativo", name.rsplit(".", 1)[0], tags


def is_dgcp_template_candidate(row: M365RepositoryFile) -> bool:
    if row.is_folder or row.is_deleted:
        return False
    name = (row.name or "").lower()
    if EXCLUDE_NAME_RE.search(name):
        return False
    if not (name.endswith(DOCX_EXT) or name.endswith(PDF_EXT)):
        return False
    path = (row.parent_path or "").lower()
    blob = f"{path} {name} {(row.document_category or '')} {(row.document_type or '')}".lower()
    if row.document_category in ("plantilla", "formulario"):
        return True
    if any(h in blob for h in DGCP_PATH_HINTS):
        return True
    if re.search(r"sncc", name, re.I):
        return True
    if re.search(r"carta|oferta|declar|pliego|formulario", name, re.I):
        return True
    return False


def score_template_row(row: M365RepositoryFile) -> int:
    score = 0
    name = (row.name or "").lower()
    path = (row.parent_path or "").lower()
    if path == "dgcp" or "02_plantillas" in path:
        score += 30
    if "dgcp" in path:
        score += 20
    if row.document_category in ("plantilla", "formulario"):
        score += 15
    if name.endswith(".docx"):
        score += 10
    if re.search(r"sncc", name):
        score += 10
    if row.document_type and row.document_type != "general":
        score += 5
    return score


def row_to_catalog_entry(row: M365RepositoryFile) -> TemplateCatalogEntry:
    category, label, tags = classify_template(row.name, row.parent_path or "", row.document_type or "")
    form_type = _form_type_from_name(row.name)
    template_key = _slugify(row.name.rsplit(".", 1)[0])
    fmt = "pdf" if row.name.lower().endswith(".pdf") else "docx"
    return TemplateCatalogEntry(
        template_key=template_key,
        form_type=form_type,
        name=row.name,
        m365_file_id=row.id,
        graph_item_id=row.graph_item_id,
        drive_id=row.drive_id,
        source=row.source,
        parent_path=row.parent_path or "",
        web_url=row.web_url,
        document_type=row.document_type or "general",
        document_category=row.document_category or "general",
        detected_category=category,
        detected_label=label,
        format=fmt,
        content_hash=row.content_hash,
        score=score_template_row(row),
        tags=tags,
    )
