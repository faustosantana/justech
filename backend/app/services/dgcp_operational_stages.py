"""Estado operativo del flujo expediente / paquete DGCP."""

from __future__ import annotations

OPERATIONAL_STAGES = (
    "DETECTADA",
    "INTERES_MARCADO",
    "EN_ANALISIS",
    "EN_PREPARACION",
    "PENDIENTE_DOCUMENTOS",
    "PENDIENTE_COTIZACION",
    "PENDIENTE_REVISION",
    "EXPEDIENTE_LISTO",
    "PAQUETE_DGCP_PREPARADO",
    "LISTA_PARA_PRESENTAR",
)

STAGE_LABELS = {
    "DETECTADA": "Detectada",
    "INTERES_MARCADO": "Interés marcado",
    "EN_ANALISIS": "En análisis",
    "EN_PREPARACION": "En preparación",
    "PENDIENTE_DOCUMENTOS": "Pendiente documentos",
    "PENDIENTE_COTIZACION": "Pendiente cotización",
    "PENDIENTE_REVISION": "Pendiente revisión",
    "EXPEDIENTE_LISTO": "Expediente listo",
    "PAQUETE_DGCP_PREPARADO": "Paquete DGCP preparado",
    "LISTA_PARA_PRESENTAR": "Lista para presentar",
}

REAL_TO_OPERATIONAL = {
    "sin_generar": "PENDIENTE_REVISION",
    "generado_incompleto": "PENDIENTE_DOCUMENTOS",
    "generado_con_observaciones": "PENDIENTE_REVISION",
    "listo_para_revision": "EXPEDIENTE_LISTO",
    "listo_para_subir": "LISTA_PARA_PRESENTAR",
    "paquete_dgcp_preparado": "PAQUETE_DGCP_PREPARADO",
    "descargado": "PAQUETE_DGCP_PREPARADO",
    "requiere_actualizacion": "PENDIENTE_REVISION",
}


def operational_stage_for_real_status(real_status: str | None) -> str:
    return REAL_TO_OPERATIONAL.get(real_status or "sin_generar", "PENDIENTE_REVISION")


def expediente_status_for_real(real_status: str | None) -> str:
    mapping = {
        "sin_generar": "sin_preparar",
        "generado_incompleto": "expediente_incompleto",
        "generado_con_observaciones": "expediente_con_documentos_vencidos",
        "listo_para_revision": "expediente_listo_para_revision",
        "listo_para_subir": "expediente_listo_para_presentar",
        "paquete_dgcp_preparado": "expediente_listo_para_presentar",
        "descargado": "expediente_listo_para_presentar",
        "requiere_actualizacion": "expediente_en_preparacion",
    }
    return mapping.get(real_status or "sin_generar", "expediente_en_preparacion")
