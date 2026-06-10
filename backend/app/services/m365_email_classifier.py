"""Motor de clasificación de correos M365."""

from __future__ import annotations

import re
from dataclasses import dataclass


EMAIL_CLASS_LABELS: dict[str, str] = {
    "cotizacion_proveedor": "Cotización proveedor",
    "orden_compra": "Orden de compra",
    "factura_proveedor": "Factura proveedor",
    "factura_cliente": "Factura cliente",
    "comprobante_pago": "Comprobante de pago",
    "licitacion": "Licitación / DGCP",
    "documento_legal": "Documento legal",
    "contrato": "Contrato",
    "ficha_tecnica": "Ficha técnica",
    "catalogo": "Catálogo",
    "presentacion_comercial": "Presentación comercial",
    "invitacion_reunion": "Invitación reunión",
    "general": "General",
}


@dataclass
class EmailClassification:
    classification: str
    confidence: int
    matched_signals: list[str]


CLASSIFICATION_RULES: list[tuple[str, tuple[str, ...], int]] = [
    ("cotizacion_proveedor", ("cotización", "cotizacion", "quote", "proforma", "adjunto cotización", "pricing"), 88),
    ("orden_compra", ("orden de compra", "purchase order", " po ", "oc cliente", "pedido"), 90),
    ("factura_proveedor", ("factura proveedor", "vendor invoice", "factura de compra", "accounts payable"), 86),
    ("factura_cliente", ("factura cliente", "invoice", "factura electrónica", "account.move"), 84),
    ("comprobante_pago", ("comprobante", "recibo de pago", "payment receipt", "transferencia"), 82),
    ("licitacion", ("licitación", "licitacion", "dgcp", "pliego", "circular", "enmienda", "lpn", "invitación a participar"), 92),
    ("documento_legal", ("documento legal", "certificación", "registro mercantil", "rpe", "sncc"), 80),
    ("contrato", ("contrato", "acuerdo", "convenio"), 78),
    ("ficha_tecnica", ("ficha técnica", "ficha tecnica", "datasheet", "spec sheet"), 85),
    ("catalogo", ("catálogo", "catalogo", "lista de precios", "price list"), 83),
    ("presentacion_comercial", ("presentación", "presentacion", "brochure", "propuesta comercial"), 75),
    ("invitacion_reunion", ("reunión", "reunion", "teams meeting", "invitación", "calendar invite"), 72),
]


VENDOR_HINTS = (
    "dell", "lenovo", "hp", "hpe", "microsoft", "cisco", "samsung", "apple",
    "distribuidor", "proveedor", "vendor",
)


class M365EmailClassifier:
    def classify(
        self,
        *,
        subject: str,
        body: str,
        sender_email: str,
        attachment_names: list[str] | None = None,
    ) -> EmailClassification:
        attachment_names = attachment_names or []
        combined = f"{subject}\n{body}\n{' '.join(attachment_names)}".lower()
        best = EmailClassification("general", 45, ["sin señal fuerte"])
        for classification, keywords, base_confidence in CLASSIFICATION_RULES:
            matched = [k for k in keywords if k in combined]
            if not matched:
                continue
            confidence = min(98, base_confidence + min(8, len(matched) * 2))
            if confidence > best.confidence:
                best = EmailClassification(classification, confidence, matched)
        if best.classification == "general" and any(v in combined or v in sender_email.lower() for v in VENDOR_HINTS):
            if any(w in combined for w in ("adjunto", "attached", "pdf", "xlsx")):
                best = EmailClassification("cotizacion_proveedor", 72, ["proveedor + adjunto"])
        return best

    @staticmethod
    def label(classification: str) -> str:
        return EMAIL_CLASS_LABELS.get(classification, classification.replace("_", " ").title())

    @staticmethod
    def dgcp_code(text: str) -> str | None:
        m = re.search(r"\b(DGCP[-\s]?\d{4}[-\s]?\d+)\b", text, re.I)
        if m:
            return m.group(1).upper().replace(" ", "-")
        m = re.search(r"\b(LPN[-\s]?\w+)\b", text, re.I)
        return m.group(1).upper() if m else None
