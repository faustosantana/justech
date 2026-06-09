"""Motor de análisis documental — entidades, resumen, riesgos, vencimientos."""

from __future__ import annotations

import re
from datetime import date, datetime

from app.schemas.document import DocumentIntelligenceResult

RNC_RE = re.compile(r"\b\d{9,11}\b")
CEDULA_RE = re.compile(r"\b\d{3}-\d{7}-\d\b|\b\d{11}\b")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}")
AMOUNT_RE = re.compile(r"(?:RD\$|USD\$|\$)\s*[\d,]+(?:\.\d{2})?|[\d,]+\.\d{2}\s*(?:DOP|USD)", re.I)
DATE_RE = re.compile(
    r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b|\b(\d{4})-(\d{2})-(\d{2})\b"
)
ODOO_REF_RE = re.compile(r"\b(?:SO|PO|INV|FAC)[-/]?\d+\b", re.I)
DGCP_REF_RE = re.compile(r"\b(?:LPN|OCID|DGCP)[-/]?\w+\b", re.I)

DOC_TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "certificacion_tss": ("tss", "seguro social", "certificación tss"),
    "certificacion_dgii": ("dgii", "certificación dgii", "impuestos internos"),
    "registro_mercantil": ("registro mercantil", "cámara de comercio"),
    "rpe": ("rpe", "registro de proveedores", "proveedor del estado"),
    "contrato": ("contrato", "acuerdo", "convenio"),
    "factura": ("factura", "invoice", "account.move"),
    "cotizacion": ("cotización", "cotizacion", "proforma", "quote"),
    "sncc": ("sncc", "f042", "f047", "f033", "formulario"),
    "licitacion": ("licitación", "licitacion", "proceso dgcp", "lpn"),
}


class DocumentIntelligenceEngine:
    def analyze(
        self,
        *,
        text: str,
        title: str,
        filename: str,
        category: str | None = None,
    ) -> DocumentIntelligenceResult:
        combined = f"{title}\n{filename}\n{text}"
        lowered = combined.lower()

        doc_type = category or self._detect_type(lowered)
        entities = self._extract_entities(combined)
        expirations = self._extract_expirations(combined, lowered)
        risks = self._detect_risks(lowered, expirations)
        recommendations = self._recommendations(doc_type, risks, expirations)
        summary = self._summary(text, title, doc_type)

        return DocumentIntelligenceResult(
            summary=summary,
            document_type=doc_type,
            entities=entities,
            risks=risks,
            expirations=expirations,
            recommendations=recommendations,
            odoo_references=list(dict.fromkeys(ODOO_REF_RE.findall(combined)))[:10],
            dgcp_references=list(dict.fromkeys(DGCP_REF_RE.findall(combined)))[:10],
        )

    @staticmethod
    def _detect_type(lowered: str) -> str:
        for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
            if any(k in lowered for k in keywords):
                return doc_type
        return "general"

    @staticmethod
    def _extract_entities(text: str) -> dict:
        return {
            "rnc": list(dict.fromkeys(RNC_RE.findall(text)))[:5],
            "cedulas": list(dict.fromkeys(CEDULA_RE.findall(text)))[:5],
            "emails": list(dict.fromkeys(EMAIL_RE.findall(text)))[:8],
            "phones": list(dict.fromkeys(PHONE_RE.findall(text)))[:5],
            "amounts": list(dict.fromkeys(AMOUNT_RE.findall(text)))[:8],
            "dates": list(dict.fromkeys(DATE_RE.findall(text)))[:12],
        }

    @staticmethod
    def _extract_expirations(text: str, lowered: str) -> list[dict]:
        items: list[dict] = []
        patterns = (
            ("vigencia", r"vigencia\s*(?:hasta|al)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
            ("vence", r"vence\s*(?:el|en)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
            ("valido_hasta", r"válido\s+hasta\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
        )
        for label, pat in patterns:
            for m in re.finditer(pat, lowered):
                items.append({"label": label, "date_raw": m.group(1)})
        if "tss" in lowered:
            items.append({"label": "certificación TSS", "keyword": "tss"})
        if "dgii" in lowered:
            items.append({"label": "certificación DGII", "keyword": "dgii"})
        if "registro mercantil" in lowered:
            items.append({"label": "Registro Mercantil", "keyword": "registro_mercantil"})
        if "rpe" in lowered:
            items.append({"label": "RPE", "keyword": "rpe"})
        return items[:10]

    @staticmethod
    def _detect_risks(lowered: str, expirations: list[dict]) -> list[str]:
        risks: list[str] = []
        if any(w in lowered for w in ("sin firma", "falta firma", "no firmado")):
            risks.append("Posible firma faltante.")
        if "vencid" in lowered:
            risks.append("El documento menciona vigencia vencida.")
        if len(expirations) > 3:
            risks.append("Múltiples fechas de vigencia detectadas — verificar consistencia.")
        if "confidencial" in lowered and "anexo" not in lowered:
            risks.append("Documento marcado como confidencial.")
        return risks

    @staticmethod
    def _recommendations(doc_type: str, risks: list[str], expirations: list[dict]) -> list[str]:
        recs: list[str] = []
        if doc_type in ("certificacion_tss", "certificacion_dgii", "rpe", "registro_mercantil"):
            recs.append("Verificar fecha de vencimiento y programar renovación.")
        if risks:
            recs.append("Revisar hallazgos de cumplimiento antes de usar en expediente.")
        if expirations:
            recs.append("Registrar vencimientos en alertas del sistema.")
        if not recs:
            recs.append("Documento indexado — disponible para búsqueda empresarial.")
        return recs

    @staticmethod
    def _summary(text: str, title: str, doc_type: str) -> str:
        clean = re.sub(r"\s+", " ", text).strip()
        if len(clean) > 400:
            snippet = clean[:400].rsplit(" ", 1)[0] + "…"
        elif clean:
            snippet = clean
        else:
            snippet = f"Documento «{title}» registrado."
        return f"[{doc_type}] {snippet}"

    @staticmethod
    def infer_metadata(text: str, title: str, filename: str) -> dict:
        combined = f"{title} {filename} {text}".lower()
        tags: list[str] = []
        keywords: list[str] = []
        company = None
        client = None
        supplier = None
        category = "general"

        for doc_type, kws in DOC_TYPE_KEYWORDS.items():
            if any(k in combined for k in kws):
                category = doc_type
                tags.append(doc_type)
                break

        for name in ("justech", "just group", "banco ademi", "ingram", "microsoft", "fortinet", "dell"):
            if name in combined:
                keywords.append(name.title() if name != "ingram" else "Ingram Micro")
                if "banco" in name:
                    client = "Banco Ademi"
                if name in ("ingram", "dell", "fortinet", "microsoft"):
                    supplier = keywords[-1]

        if "justech" in combined or "just group" in combined:
            company = "Justech" if "justech" in combined else "Just Group"

        return {
            "category": category,
            "tags": list(dict.fromkeys(tags + keywords))[:15],
            "keywords": list(dict.fromkeys(keywords))[:15],
            "company": company,
            "client_name": client,
            "supplier_name": supplier,
        }

    @staticmethod
    def parse_valid_until(text: str) -> date | None:
        for m in DATE_RE.finditer(text):
            try:
                if m.group(4):
                    return date(int(m.group(4)), int(m.group(5)), int(m.group(6)))
                y = int(m.group(3))
                if y < 100:
                    y += 2000
                return date(y, int(m.group(2)), int(m.group(1)))
            except ValueError:
                continue
        return None
