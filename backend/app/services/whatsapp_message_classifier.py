"""Clasificación de mensajes WhatsApp — reglas empresariales JAIOS."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


CLASSIFICATION_LABELS: dict[str, str] = {
    "cliente": "Cliente",
    "proveedor": "Proveedor",
    "oportunidad": "Oportunidad comercial",
    "licitacion": "Licitación / DGCP",
    "soporte": "Soporte",
    "cobro": "Cobro / facturación",
    "seguimiento": "Seguimiento",
    "reclamo": "Reclamo",
    "urgencia": "Urgencia",
}


@dataclass
class WhatsappClassification:
    classification: str
    confidence: int
    secondary_labels: list[str] = field(default_factory=list)
    priority: int = 50
    sentiment: str = "neutral"
    signals: list[str] = field(default_factory=list)
    entities: dict = field(default_factory=dict)


RULES: list[tuple[str, tuple[str, ...], int, int]] = [
    ("licitacion", ("licitación", "licitacion", "rfp", "concurso", "dgcp", "compra pública", "pliego", "lpn"), 92, 85),
    ("oportunidad", ("cotización", "cotizacion", "propuesta", "oferta", "presupuesto", "necesito", "requiero"), 86, 70),
    ("cobro", ("pago", "factura", "cobro", "vencimiento", "transferencia", "pendiente de pago"), 84, 65),
    ("soporte", ("error", "soporte", "ayuda", "ticket", "no funciona", "falla"), 82, 72),
    ("reclamo", ("reclamo", "queja", "insatisfecho", "mal servicio", "devolución"), 88, 80),
    ("urgencia", ("urgente", "asap", "hoy", "inmediato", "prioridad"), 90, 90),
    ("proveedor", ("proveedor", "distribuidor", "ingram", "omega", "dell", "lenovo", "hp"), 80, 55),
    ("cliente", ("cliente", "empresa", "compra", "adquirir", "solicito"), 78, 60),
]


PRODUCT_PATTERN = re.compile(
    r"(?:(\d+)\s+)?(laptops?|notebooks?|servidores?|licencias?|monitores?|impresoras?|switches?|routers?|ups|computadoras?)\s*([\w\-]+)?",
    re.I,
)


class WhatsappMessageClassifier:
    def classify(self, *, text: str, contact_name: str | None = None) -> WhatsappClassification:
        lower = (text or "").lower()
        best = WhatsappClassification(classification="seguimiento", confidence=55, priority=40)

        for label, keywords, conf, priority in RULES:
            matched = [k for k in keywords if k in lower]
            if matched:
                if conf > best.confidence:
                    secondary = [best.classification] if best.classification != "seguimiento" else []
                    best = WhatsappClassification(
                        classification=label,
                        confidence=conf,
                        secondary_labels=secondary,
                        priority=priority,
                        signals=matched[:5],
                    )
                elif label not in best.secondary_labels:
                    best.secondary_labels.append(label)

        if any(w in lower for w in ("gracias", "excelente", "perfecto")):
            best.sentiment = "positive"
        elif any(w in lower for w in ("problema", "reclamo", "mal", "retraso", "error")):
            best.sentiment = "negative"

        products: list[str] = []
        for m in PRODUCT_PATTERN.finditer(text or ""):
            qty, kind, brand = m.group(1), m.group(2), m.group(3)
            phrase = " ".join(p for p in [qty, kind, brand] if p)
            if phrase:
                products.append(phrase.strip())

        entities: dict = {"products": products}
        if contact_name:
            entities["contact_name"] = contact_name

        company_match = re.search(
            r"(?:banco|empresa|institución|ministerio|hospital|colegio)\s+[\w\s]{2,40}",
            text or "",
            re.I,
        )
        if company_match:
            entities["company"] = company_match.group(0).strip()

        best.entities = entities
        return best
