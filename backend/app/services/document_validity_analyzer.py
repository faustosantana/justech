"""Análisis de vigencia desde contenido real del documento (Fase 7.3 QA)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from app.services.document_extraction_service import DocumentExtractionService
from app.services.document_intelligence_engine import DocumentIntelligenceEngine
from app.services.vigency_engine import VigencyEngine

SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

VIGENCY_REQUIREMENT_KEYS = frozenset({
    "certificacion_tss",
    "certificacion_dgii",
    "registro_mercantil",
    "certificacion_mipyme",
})

OPTIONAL_VIGENCY_KEYS = frozenset({
    "autorizacion_fabricante",
    "carta_fabricante",
    "carta_presentacion",
    "poder_autorizacion",
})

EXPIRY_PATTERNS: tuple[tuple[str, str, bool], ...] = (
    ("valido_hasta", r"(?:v[aá]lid[ao]|vigente)\s+hasta(?:\s+el)?[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", True),
    ("valido_hasta_text", r"(?:v[aá]lid[ao]|vigente)\s+hasta\s+el\s+d[ií]a\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", True),
    ("fecha_vencimiento", r"fecha de vencimiento[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", True),
    ("vence_el", r"vence\s+el[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", True),
    ("vigencia_hasta", r"vigencia\s*(?:hasta|al)?[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", True),
    ("expira", r"expira[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", True),
    ("periodo_valido", r"per[ií]odo\s+v[aá]lid[ao][:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", True),
    ("iso_expiry", r"(?:vencimiento|vigencia|expira)[^\d]{0,30}(\d{4}-\d{2}-\d{2})", True),
    ("valido_hasta_text2", r"v[aá]lid[ao]\s+hasta\s+el\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", True),
    ("cert_valida", r"certificaci[oó]n\s+(?:es\s+)?v[aá]lid[ao]\s+hasta[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", True),
)

ISSUE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("emitido", r"(?:emitido|expedido|fecha de emisi[oó]n|certificaci[oó]n emitida)[^\d]{0,20}(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
    ("emitido_text", r"(?:emitido|expedido)\s+el\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})"),
)


@dataclass
class DocumentValidityResult:
    document_id: str | None = None
    document_name: str = ""
    document_type: str = ""
    issue_date: date | None = None
    expiration_date: date | None = None
    validity_status: str = VigencyEngine.SIN_FECHA
    confidence: str = "baja"
    evidence_text: str | None = None
    evidence_page: int | None = None
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extracted_text_length: int = 0
    text_analyzed: bool = False
    requirement_status: str = "encontrado_sin_analizar"
    vigency_status: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "document_type": self.document_type,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "validity_status": self.validity_status,
            "confidence": self.confidence,
            "evidence_text": self.evidence_text,
            "evidence_page": self.evidence_page,
            "analyzed_at": self.analyzed_at.isoformat(),
            "extracted_text_length": self.extracted_text_length,
            "text_analyzed": self.text_analyzed,
            "requirement_status": self.requirement_status,
            "vigency_status": self.vigency_status,
            "note": self.note,
        }


class DocumentValidityAnalyzer:
    """Lee texto interno del documento y determina vigencia con evidencia."""

    def __init__(self) -> None:
        self.vigency = VigencyEngine()
        self.intelligence = DocumentIntelligenceEngine()
        self.extractor = DocumentExtractionService()

    @staticmethod
    def requires_vigency_check(requirement_key: str) -> bool:
        return requirement_key in VIGENCY_REQUIREMENT_KEYS

    @staticmethod
    def supports_optional_vigency(requirement_key: str) -> bool:
        return requirement_key in OPTIONAL_VIGENCY_KEYS

    def analyze_document(
        self,
        requirement_key: str,
        *,
        text: str | None = None,
        title: str = "",
        filename: str = "",
        content: bytes | None = None,
        document_id: str | None = None,
        pages: list[str] | None = None,
    ) -> DocumentValidityResult:
        body = (text or "").strip()
        page_list = pages or []

        if not body and content:
            extraction = self.extractor.extract(content, filename=filename or title)
            body = (extraction.text or "").strip()
            page_list = extraction.pages or page_list

        result = DocumentValidityResult(
            document_id=document_id,
            document_name=title or filename,
            document_type=requirement_key,
            extracted_text_length=len(body),
            text_analyzed=bool(body),
        )

        if not body:
            result.validity_status = "requiere_revision"
            result.requirement_status = "encontrado_sin_analizar"
            result.vigency_status = "sin_texto"
            result.note = "Documento encontrado — contenido no extraído; requiere revisión manual"
            result.confidence = "baja"
            return result

        issue_date, issue_evidence, issue_page = self._find_issue_date(body, page_list)
        expiry_date, expiry_evidence, expiry_page, confidence = self._find_expiry_date(body, page_list)

        result.issue_date = issue_date
        result.expiration_date = expiry_date
        result.evidence_text = expiry_evidence or issue_evidence
        result.evidence_page = expiry_page or issue_page
        result.confidence = confidence

        if expiry_date:
            result.validity_status = self.vigency.classify(expiry_date)
            result.vigency_status = result.validity_status
            result.requirement_status = self._map_validity_to_status(
                result.validity_status, requirement_key, has_expiry=True
            )
            result.note = f"Vigencia detectada en documento ({expiry_date.isoformat()})"
            if expiry_evidence:
                result.note = f"{result.note} — «{expiry_evidence[:80]}»"
            return result

        if requirement_key == "rpe":
            result.validity_status = "no_aplica_vigencia"
            result.vigency_status = "no_aplica_vigencia"
            result.requirement_status = "encontrado_vigente"
            result.note = "RPE encontrado y leído — sin fecha de vigencia explícita en documento"
            result.confidence = "alta"
            return result

        if self.requires_vigency_check(requirement_key):
            result.validity_status = VigencyEngine.SIN_FECHA
            result.vigency_status = VigencyEngine.SIN_FECHA
            result.requirement_status = "encontrado_sin_fecha"
            result.note = "Encontrado, pero vigencia no verificada en el contenido del documento"
            result.confidence = "media" if len(body) > 200 else "baja"
            return result

        result.validity_status = "no_aplica_vigencia"
        result.vigency_status = "no_aplica_vigencia"
        result.requirement_status = "encontrado_vigente"
        result.note = "Documento corporativo encontrado y leído"
        result.confidence = "alta"
        return result

    def resolve_requirement_match(
        self,
        requirement_key: str,
        *,
        text: str | None = None,
        title: str = "",
        filename: str = "",
        content: bytes | None = None,
        document_id: str | None = None,
    ) -> tuple[str, date | None, str, str | None, DocumentValidityResult]:
        analysis = self.analyze_document(
            requirement_key,
            text=text,
            title=title,
            filename=filename,
            content=content,
            document_id=document_id,
        )
        valid_until = analysis.expiration_date
        return (
            analysis.requirement_status,
            valid_until,
            analysis.vigency_status or analysis.validity_status,
            analysis.note,
            analysis,
        )

    def _find_expiry_date(
        self,
        body: str,
        pages: list[str],
    ) -> tuple[date | None, str | None, int | None, str]:
        combined = body
        lowered = combined.lower()

        for label, pattern, _ in EXPIRY_PATTERNS:
            match = re.search(pattern, lowered, re.I)
            if not match:
                continue
            parsed = self._parse_match(match)
            if parsed:
                page_num = self._page_for_phrase(pages, match.group(0))
                return parsed, match.group(0)[:160], page_num, "alta"

        for page_idx, page in enumerate(pages or [body], start=1):
            page_lower = page.lower()
            for label, pattern, _ in EXPIRY_PATTERNS:
                match = re.search(pattern, page_lower, re.I)
                if not match:
                    continue
                parsed = self._parse_match(match)
                if parsed:
                    return parsed, match.group(0)[:160], page_idx, "alta"

        intel = self.intelligence.analyze(text=body, title="", filename="")
        for exp in intel.expirations:
            raw = exp.get("date_raw")
            if not raw:
                continue
            parsed = self._parse_date_raw(str(raw))
            if parsed:
                return parsed, str(raw), None, "media"

        fallback = self.intelligence.parse_valid_until(body)
        if fallback:
            return fallback, fallback.isoformat(), None, "media"

        near_expiry = re.findall(
            r"(?:venc|vigenc|expir|v[aá]lid)[^\d]{0,40}(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            lowered,
            re.I,
        )
        for raw in near_expiry:
            parsed = self._parse_date_raw(raw)
            if parsed:
                return parsed, raw, None, "media"

        return None, None, None, "baja"

    def _find_issue_date(
        self,
        body: str,
        pages: list[str],
    ) -> tuple[date | None, str | None, int | None]:
        lowered = body.lower()
        for _, pattern in ISSUE_PATTERNS:
            match = re.search(pattern, lowered, re.I)
            if not match:
                continue
            parsed = self._parse_match(match)
            if parsed:
                return parsed, match.group(0)[:120], self._page_for_phrase(pages, match.group(0))
        return None, None, None

    @staticmethod
    def _page_for_phrase(pages: list[str], phrase: str) -> int | None:
        if not pages:
            return None
        snippet = phrase[:40].lower()
        for idx, page in enumerate(pages, start=1):
            if snippet and snippet in page.lower():
                return idx
        return 1 if pages else None

    def _parse_match(self, match: re.Match[str]) -> date | None:
        groups = match.groups()
        if len(groups) == 3 and groups[1] and not groups[1][0].isdigit():
            day = int(groups[0])
            month_name = groups[1].lower()
            year = int(groups[2])
            month = SPANISH_MONTHS.get(month_name)
            if month:
                try:
                    return date(year, month, day)
                except ValueError:
                    return None
        if groups[0]:
            return self._parse_date_raw(groups[0])
        return None

    @staticmethod
    def _parse_date_raw(raw: str) -> date | None:
        cleaned = raw.strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y"):
            try:
                parsed = datetime.strptime(cleaned, fmt).date()
                if parsed.year < 100:
                    parsed = parsed.replace(year=parsed.year + 2000)
                return parsed
            except ValueError:
                continue
        return None

    @staticmethod
    def _map_validity_to_status(validity_status: str, requirement_key: str, *, has_expiry: bool) -> str:
        if validity_status == VigencyEngine.VENCIDO:
            return "encontrado_vencido"
        if validity_status == VigencyEngine.PROXIMO:
            return "requiere_revision"
        if validity_status == VigencyEngine.VIGENTE:
            return "encontrado_vigente"
        if has_expiry:
            return "requiere_revision"
        if DocumentValidityAnalyzer.requires_vigency_check(requirement_key):
            return "encontrado_sin_fecha"
        return "encontrado_vigente"
