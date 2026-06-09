"""Política de contexto del Assistant — cuándo aplicar record_type vs intención del texto."""

from __future__ import annotations

import re

from app.services.business_intent_router import BusinessIntent, ParsedBusinessQuestion

# Intenciones que NUNCA deben ser secuestradas por record_type pegado.
NON_RECORD_INTENTS = frozenset({
    BusinessIntent.PRICE,
    BusinessIntent.SALES,
    BusinessIntent.PURCHASE,
    BusinessIntent.TASKS,
    BusinessIntent.ENTERPRISE_SEARCH,
    BusinessIntent.M365,
    BusinessIntent.CUSTOMER_FINANCE,
    BusinessIntent.SUPPLIER,
})

DGCP_RECORD_PHRASES = (
    "esta licitación",
    "este proceso",
    "este pliego",
    "este tdr",
    "este expediente",
    "qué pide esta",
    "que pide esta",
    "qué pide el pliego",
    "que pide el pliego",
    "requisito de esta",
    "requisitos de esta",
    "faltan para esta",
    "checklist de esta",
    "preparación de esta",
    "preparacion de esta",
    "porcentaje del expediente",
    "expediente está listo",
    "expediente esta listo",
    "preparación del expediente",
    "preparacion del expediente",
    "oferta técnica",
    "oferta tecnica",
    "oferta económica",
    "oferta economica",
    "mostrar interés",
    "mostrar interes",
)

INVOICE_RECORD_PHRASES = ("esta factura", "este invoice", "factura actual", "líneas de esta factura")
CUSTOMER_RECORD_PHRASES = ("este cliente", "cliente actual", "historial de este cliente")
PRODUCT_RECORD_PHRASES = ("este producto", "producto actual", "precio de este producto")


def _has_deictic_dgcp(lowered: str) -> bool:
    return bool(
        re.search(r"\b(esta|este|estos|estas)\s+(licitaci|proceso|pliego|expediente|oferta|tdr)", lowered)
    )


def is_dgcp_record_question(question: str, classified: ParsedBusinessQuestion) -> bool:
    lowered = question.strip().lower()
    if classified.intent in NON_RECORD_INTENTS:
        return False
    if classified.intent == BusinessIntent.DOCUMENT and not any(
        k in lowered for k in ("expediente", "pliego", "tdr", "sncc", "licitaci")
    ):
        return False
    if classified.intent == BusinessIntent.DGCP:
        return True
    if any(p in lowered for p in DGCP_RECORD_PHRASES):
        return True
    if _has_deictic_dgcp(lowered):
        return True
    if any(k in lowered for k in ("pliego", "tdr", "requisito", "checklist", "expediente")) and (
        "licit" in lowered or _has_deictic_dgcp(lowered)
    ):
        return True
    return False


def is_invoice_record_question(question: str, classified: ParsedBusinessQuestion) -> bool:
    if classified.intent in NON_RECORD_INTENTS:
        return False
    lowered = question.lower()
    return any(p in lowered for p in INVOICE_RECORD_PHRASES) or (
        classified.intent == BusinessIntent.CUSTOMER_FINANCE and "factura" in lowered
    )


def is_customer_record_question(question: str, classified: ParsedBusinessQuestion) -> bool:
    if classified.intent in NON_RECORD_INTENTS:
        return False
    lowered = question.lower()
    return any(p in lowered for p in CUSTOMER_RECORD_PHRASES)


def is_product_record_question(question: str, classified: ParsedBusinessQuestion) -> bool:
    if classified.intent in NON_RECORD_INTENTS:
        return False
    lowered = question.lower()
    return any(p in lowered for p in PRODUCT_RECORD_PHRASES) or (
        classified.intent == BusinessIntent.PRICE and "este producto" in lowered
    )


def module_context_label(current_module: str | None, record_type: str | None, record_id: str | None) -> str:
    path = (current_module or "/").rstrip("/") or "/"
    if record_type in ("dgcp", "dgcp_opportunity") and record_id:
        return f"DGCP — proceso {record_id[:8]}…"
    if path.startswith("/prices"):
        return "Inteligencia de Precios"
    if path.startswith("/documents"):
        return "Documentos"
    if path.startswith("/odoo"):
        return "Odoo"
    if path.startswith("/tasks"):
        return "Tareas"
    if path.startswith("/work"):
        return "Centro de trabajo"
    if path.startswith("/dgcp"):
        return "DGCP"
    if path.startswith("/search"):
        return "Búsqueda empresarial"
    if path.startswith("/dashboard"):
        return "Panel principal"
    if path.startswith("/m365"):
        return "Microsoft 365"
    if path.startswith("/admin"):
        return "Administración"
    return "JAIOS"
