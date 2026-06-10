"""Extracción de entidades desde correos y adjuntos M365."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.services.document_intelligence_engine import DocumentIntelligenceEngine
from app.services.m365_email_classifier import M365EmailClassifier, VENDOR_HINTS


PRODUCT_PATTERNS = (
    r"\b(latitude\s*\d+)",
    r"\b(optiplex\s*\d+)",
    r"\b(poweredge\s*\d+)",
    r"\b(monitor\s+\w+)",
    r"\b(laptop\s+\w+)",
    r"\b(toner\s+\w+)",
    r"\b(papel\s+\d+)",
)

KNOWN_VENDORS = (
    ("dell", "Dell"),
    ("lenovo", "Lenovo"),
    ("hp ", "HP"),
    ("hpe", "HPE"),
    ("microsoft", "Microsoft"),
    ("cisco", "Cisco"),
    ("samsung", "Samsung"),
)

KNOWN_CLIENTS = (
    ("ademi", "Banco Ademi"),
    ("banco ademi", "Banco Ademi"),
    ("capital dbg", "Capital DBG"),
    ("ministerio", "Institución pública"),
)


class M365EmailExtractionService:
    def __init__(self) -> None:
        self._doc_engine = DocumentIntelligenceEngine()
        self._classifier = M365EmailClassifier()

    def extract(
        self,
        *,
        subject: str,
        body: str,
        sender_email: str,
        sender_name: str | None,
        attachment_texts: list[tuple[str, str]] | None = None,
    ) -> dict:
        attachment_texts = attachment_texts or []
        combined = f"{subject}\n{body}\n" + "\n".join(t for _, t in attachment_texts)
        doc = self._doc_engine.analyze(
            text=combined,
            title=subject,
            filename=attachment_texts[0][0] if attachment_texts else "email.txt",
        )
        vendor = self._detect_vendor(combined, sender_email, sender_name)
        client = self._detect_client(combined)
        amount, currency = self._detect_amount(combined, doc.entities.get("amounts", []))
        products = self._detect_products(combined)
        dgcp_code = self._classifier.dgcp_code(combined)
        document_number = self._detect_document_number(combined)
        contact = sender_name or sender_email.split("@")[0]
        return {
            "vendor": vendor,
            "client": client,
            "dgcp_process_code": dgcp_code,
            "amount": float(amount) if amount is not None else None,
            "currency": currency,
            "document_number": document_number,
            "products": products,
            "contact_name": contact,
            "contact_email": sender_email,
            "rnc": (doc.entities.get("rnc") or [None])[0],
            "document_type": doc.document_type,
            "dates": doc.entities.get("dates", [])[:5],
            "odoo_references": doc.odoo_references,
            "dgcp_references": doc.dgcp_references,
            "summary": doc.summary,
        }

    @staticmethod
    def _detect_vendor(text: str, sender_email: str, sender_name: str | None) -> str | None:
        lowered = text.lower()
        domain = sender_email.split("@")[-1].lower()
        for hint, label in KNOWN_VENDORS:
            if hint in lowered or hint.strip() in domain:
                return label
        if sender_name:
            for hint, label in KNOWN_VENDORS:
                if hint in sender_name.lower():
                    return label
        for hint in VENDOR_HINTS:
            if hint in lowered:
                return hint.title()
        return None

    @staticmethod
    def _detect_client(text: str) -> str | None:
        lowered = text.lower()
        for hint, label in KNOWN_CLIENTS:
            if hint in lowered:
                return label
        return None

    @staticmethod
    def _detect_amount(text: str, amount_strings: list[str]) -> tuple[Decimal | None, str | None]:
        currency = None
        if "usd" in text.lower() or "US$" in text or "USD" in text:
            currency = "USD"
        elif "rd$" in text.lower() or "dop" in text.lower():
            currency = "DOP"
        patterns = [
            r"(?:USD|US\$|RD\$|\$)\s*([\d,]+(?:\.\d{2})?)",
            r"([\d,]+(?:\.\d{2})?)\s*(?:USD|DOP)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.I)
            if m:
                try:
                    value = Decimal(m.group(1).replace(",", ""))
                    if not currency and "USD" in m.group(0).upper():
                        currency = "USD"
                    if not currency:
                        currency = "USD" if value > 1000 and "12" in m.group(1) else "DOP"
                    return value, currency or "USD"
                except (InvalidOperation, ValueError):
                    continue
        for raw in amount_strings[:3]:
            m = re.search(r"([\d,]+(?:\.\d{2})?)", str(raw))
            if m:
                try:
                    return Decimal(m.group(1).replace(",", "")), currency or "DOP"
                except (InvalidOperation, ValueError):
                    pass
        return None, currency

    @staticmethod
    def _detect_products(text: str) -> list[str]:
        found: list[str] = []
        for pattern in PRODUCT_PATTERNS:
            for m in re.finditer(pattern, text, re.I):
                label = m.group(1).strip()
                if label.lower() not in {x.lower() for x in found}:
                    found.append(label.title())
        if "latitude" in text.lower() and not any("latitude" in p.lower() for p in found):
            found.append("Latitude")
        if "optiplex" in text.lower() and not any("optiplex" in p.lower() for p in found):
            found.append("Optiplex")
        if "monitor" in text.lower() and not any("monitor" in p.lower() for p in found):
            found.append("Monitor")
        return found[:12]

    @staticmethod
    def _detect_document_number(text: str) -> str | None:
        for pattern in (r"\b(?:FAC|INV|PO|OC|COT)[-/]?\d+\b", r"\b\d{3}-\d{7}-\d\b"):
            m = re.search(pattern, text, re.I)
            if m:
                return m.group(0).upper()
        return None
