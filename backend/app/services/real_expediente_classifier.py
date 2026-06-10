"""Clasificación de documentos para expediente real DGCP."""

from __future__ import annotations

from app.services.document_finalization_rules import REQUIREMENTS_REQUIRING_FINALIZATION

REAL_EXPEDIENTE_FOLDERS = (
    "01_Documentos_Legales",
    "02_Formularios",
    "03_Oferta_Tecnica",
    "04_Oferta_Economica",
    "05_Fichas_Tecnicas",
    "06_Cartas_Fabricante",
    "07_Revision",
    "08_Listo_Para_Subir",
)

LEGAL_KEY_FRAGMENTS = (
    "rpe",
    "dgii",
    "tss",
    "registro_mercantil",
    "mipyme",
    "cedula",
    "representante",
    "acta",
    "poder",
    "estatuto",
    "certificacion",
    "documento_legal",
)

FORM_KEY_FRAGMENTS = (
    "sncc",
    "f033",
    "f034",
    "f042",
    "f047",
    "carta_presentacion",
    "declaracion",
    "formulario",
)

TECH_KEY_FRAGMENTS = (
    "oferta_tecnica",
    "propuesta_tecnica",
    "tecnico",
    "metodologia",
    "cronograma",
    "experiencia",
    "personal",
    "cumplimiento_tecnico",
)

ECONOMIC_KEY_FRAGMENTS = (
    "oferta_economica",
    "propuesta_economica",
    "financiero",
    "cotizacion",
    "precio",
)

FICHA_KEY_FRAGMENTS = (
    "ficha_tecnica",
    "datasheet",
    "brochure",
    "catalogo",
    "especificacion",
)

FABRICANTE_KEY_FRAGMENTS = (
    "fabricante",
    "distribuidor",
    "autorizacion",
    "garantia_fabricante",
    "carta_fabricante",
    "proveedor_fabricante",
)

FALTANTE_STATUSES = frozenset({"faltante", "pendiente", "borrador_pendiente"})
VENCIDO_STATUSES = frozenset({"encontrado_vencido", "vencido"})
REVIEW_STATUSES = frozenset({
    "requiere_revision",
    "encontrado_sin_fecha",
    "requiere_actualizacion",
    "encontrado_sin_analizar",
    "requiere_completado",
    "incompleto",
    "plantilla_disponible",
})
READY_STATUSES = frozenset({
    "encontrado_vigente",
    "validado_manual",
    "no_aplica",
    "adjuntado",
    "finalizado",
    "pdf_final_generado",
})


def classify_requirement(requirement_key: str, tipo: str = "") -> str:
    key = (requirement_key or "").lower()
    t = (tipo or "").lower()
    combined = f"{key} {t}"

    if any(f in combined for f in FABRICANTE_KEY_FRAGMENTS):
        return "06_Cartas_Fabricante"
    if key in REQUIREMENTS_REQUIRING_FINALIZATION or any(f in combined for f in FORM_KEY_FRAGMENTS):
        if "economica" in combined or key in ("oferta_economica", "propuesta_economica"):
            return "04_Oferta_Economica"
        if "tecnica" in combined or key in ("oferta_tecnica", "propuesta_tecnica"):
            return "03_Oferta_Tecnica"
        return "02_Formularios"
    if any(f in combined for f in ECONOMIC_KEY_FRAGMENTS):
        return "04_Oferta_Economica"
    if any(f in combined for f in TECH_KEY_FRAGMENTS):
        return "03_Oferta_Tecnica"
    if any(f in combined for f in FICHA_KEY_FRAGMENTS):
        return "05_Fichas_Tecnicas"
    if any(f in combined for f in LEGAL_KEY_FRAGMENTS) or t == "legal":
        return "01_Documentos_Legales"
    if t == "administrativo":
        return "02_Formularios"
    if t == "tecnico":
        return "03_Oferta_Tecnica"
    if t == "financiero":
        return "04_Oferta_Economica"
    return "07_Revision"


def is_ready_for_upload(
    *,
    requirement_key: str,
    status: str,
    filename: str | None,
    mandatory: bool = True,
) -> tuple[bool, str]:
    st = status or "faltante"
    if st in FALTANTE_STATUSES:
        return False, "Requisito faltante"
    if st in VENCIDO_STATUSES:
        return False, "Documento vencido"
    if st in REVIEW_STATUSES:
        return False, "Requiere revisión o completado"
    if requirement_key in REQUIREMENTS_REQUIRING_FINALIZATION and st not in (
        "finalizado",
        "pdf_final_generado",
        "validado_manual",
    ):
        return False, "Requiere PDF final firmado/sellado"
    if not filename:
        return False, "Sin archivo asociado"
    lower = filename.lower()
    if lower.endswith((".docx", ".doc", ".json", ".txt")) and requirement_key in REQUIREMENTS_REQUIRING_FINALIZATION:
        return False, "Solo PDF final permitido en Listo Para Subir"
    if lower.startswith("falta_"):
        return False, "Placeholder — no es documento final"
    if st not in READY_STATUSES and mandatory:
        return False, f"Estado no validado: {st}"
    return True, ""


def compute_real_expediente_status(
    *,
    missing_count: int,
    expired_count: int,
    review_count: int,
    ready_count: int,
    mandatory_total: int,
    marked_ready_upload: bool = False,
    marked_ready_review: bool = False,
) -> str:
    if mandatory_total == 0:
        return "generado_incompleto"
    if missing_count > 0:
        return "generado_incompleto"
    if expired_count > 0 or review_count > 0:
        if marked_ready_upload:
            return "listo_para_subir"
        return "generado_con_observaciones"
    if ready_count >= mandatory_total and marked_ready_upload:
        return "listo_para_subir"
    if ready_count >= mandatory_total and marked_ready_review:
        return "listo_para_revision"
    if ready_count >= mandatory_total:
        return "listo_para_revision"
    return "generado_incompleto"
