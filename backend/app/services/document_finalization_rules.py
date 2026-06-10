"""Reglas de documentos que requieren firma/sello y estados de finalización."""

from __future__ import annotations

FINALIZATION_STATUSES = frozenset({
    "generado",
    "pendiente_firma",
    "pendiente_sello",
    "firmado",
    "sellado",
    "pdf_final_generado",
    "finalizado",
    "requiere_revision",
})

FINALIZED_COMPLIANT_STATUSES = frozenset({"pdf_final_generado", "finalizado", "validado_manual"})

REQUIREMENTS_REQUIRING_FINALIZATION = frozenset({
    "sncc_f033",
    "sncc_f034",
    "sncc_f042",
    "sncc_f047",
    "carta_presentacion",
    "oferta_economica",
    "oferta_tecnica",
    "propuesta_tecnica",
    "propuesta_economica",
})

FORM_TYPE_TO_REQUIREMENT = {
    "SNCC.F033": "sncc_f033",
    "SNCC.F034": "sncc_f034",
    "SNCC.F042": "sncc_f042",
    "SNCC.F047": "sncc_f047",
    "OFERTA.ECONOMICA": "oferta_economica",
    "CARTA.PRESENTACION": "carta_presentacion",
}

REQUIREMENT_TO_EXPEDIENTE_FOLDER = {
    "sncc_f033": "02_Formularios_SNCC",
    "sncc_f034": "02_Formularios_SNCC",
    "sncc_f042": "02_Formularios_SNCC",
    "sncc_f047": "02_Formularios_SNCC",
    "carta_presentacion": "02_Formularios_SNCC",
    "oferta_economica": "04_Oferta_Economica",
    "oferta_tecnica": "03_Oferta_Tecnica",
    "propuesta_tecnica": "03_Oferta_Tecnica",
    "propuesta_economica": "04_Oferta_Economica",
}

REQUIREMENT_OUTPUT_BASENAME = {
    "sncc_f033": "SNCC_F033_FINAL.pdf",
    "sncc_f034": "SNCC_F034_FINAL.pdf",
    "sncc_f042": "SNCC_F042_FINAL.pdf",
    "sncc_f047": "SNCC_F047_FINAL.pdf",
    "carta_presentacion": "CARTA_PRESENTACION_FINAL.pdf",
    "oferta_economica": "OFERTA_ECONOMICA_FINAL.pdf",
    "oferta_tecnica": "OFERTA_TECNICA_FINAL.pdf",
    "propuesta_tecnica": "OFERTA_TECNICA_FINAL.pdf",
    "propuesta_economica": "OFERTA_ECONOMICA_FINAL.pdf",
}


def requires_finalization(requirement_key: str) -> bool:
    return requirement_key in REQUIREMENTS_REQUIRING_FINALIZATION


def is_finalized_status(status: str) -> bool:
    return status in FINALIZED_COMPLIANT_STATUSES
