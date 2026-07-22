"""Clasificación automática de archivos M365 (OneDrive / SharePoint)."""

from __future__ import annotations

from dataclasses import dataclass

from app.services.knowledge_classifier import KnowledgeClassifier

CATEGORY_LABELS: dict[str, str] = {
    "legal": "Documentos legales",
    "formulario": "Formularios",
    "constitucion": "Constitución / estatutos",
    "plantilla": "Plantillas",
    "contrato": "Contratos",
    "proveedor": "Proveedores",
    "licitacion": "Licitaciones",
    "financiero": "Finanzas",
    "ficha_tecnica": "Fichas técnicas",
    "cotizacion": "Cotizaciones",
    "datos_empresa": "Datos empresa",
    "general": "General",
}

CONSTITUCION_TYPES = frozenset(
    {"estatutos", "registro_mercantil", "acta", "poder", "rnc", "rpe", "dgii", "tss", "certificacion_bancaria"}
)
FORMULARIO_TYPES = frozenset({"sncc_f033", "sncc_f034", "sncc_f042", "sncc_f047", "sncc_d040"})
LEGAL_TYPES = frozenset({"contrato", "carta", "cedula", "poder", "certificacion_fabricante", "mipymes"})


@dataclass
class M365FileClassification:
    document_category: str
    document_type: str
    folder_category: str
    confidence: int
    tags: list[str]
    company_key: str | None
    label: str


class M365FileClassifier:
    def __init__(self) -> None:
        self._kc = KnowledgeClassifier()

    def classify(self, *, name: str, parent_path: str = "", mime_type: str | None = None) -> M365FileClassification:
        rel = f"{parent_path}/{name}".strip("/")
        result = self._kc.classify(relative_path=rel, filename=name, folder_name=parent_path.split("/")[-1] if parent_path else "")
        doc_type = result.document_type
        folder_cat = result.folder_category

        category = self._map_category(doc_type, folder_cat, name, parent_path)
        confidence = 70
        if doc_type != "general":
            confidence = 88
        if folder_cat != "general":
            confidence = max(confidence, 82)
        if any(t.startswith("sncc") for t in result.tags):
            confidence = 92

        tags = list(dict.fromkeys(result.tags + [category]))
        if mime_type:
            tags.append(mime_type.split("/")[-1])

        return M365FileClassification(
            document_category=category,
            document_type=doc_type,
            folder_category=folder_cat,
            confidence=confidence,
            tags=tags,
            company_key=result.company_key,
            label=CATEGORY_LABELS.get(category, category.replace("_", " ").title()),
        )

    def _map_category(self, doc_type: str, folder_cat: str, name: str, path: str) -> str:
        blob = f"{path} {name}".lower()
        if doc_type in CONSTITUCION_TYPES or any(k in blob for k in ("estatuto", "constitucion", "registro mercantil", "acta constitutiva")):
            return "constitucion"
        if doc_type in FORMULARIO_TYPES or "formulario" in blob or "sncc" in blob:
            return "formulario"
        if folder_cat == "legal" or doc_type in LEGAL_TYPES:
            return "legal"
        if folder_cat == "plantilla" or "plantilla" in blob:
            return "plantilla"
        if doc_type == "contrato" or "contrato" in blob:
            return "contrato"
        if folder_cat == "proveedor" or "proveedor" in blob:
            return "proveedor"
        if any(k in blob for k in ("licitacion", "licitación", "dgcp", "pliego", "oferta")):
            return "licitacion"
        if any(k in blob for k in ("factura", "pago", "finanz")):
            return "financiero"
        if folder_cat == "ficha_tecnica" or doc_type == "ficha_tecnica":
            return "ficha_tecnica"
        if folder_cat == "cotizacion" or doc_type in ("oferta_economica", "lista_precios"):
            return "cotizacion"
        if folder_cat == "datos_empresa":
            return "datos_empresa"
        return "general"
