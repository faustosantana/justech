"""Extracción de vigencias — delega en DocumentValidityAnalyzer (Fase 7.3)."""

from __future__ import annotations

from datetime import date

from app.services.document_validity_analyzer import (
    DocumentValidityAnalyzer,
    DocumentValidityResult,
    VIGENCY_REQUIREMENT_KEYS,
)
from app.services.vigency_engine import VigencyEngine

# Re-export for backward compatibility
VigencyExtractionResult = DocumentValidityResult


class DocumentVigencyExtractor:
    def __init__(self) -> None:
        self.analyzer = DocumentValidityAnalyzer()

    @staticmethod
    def requires_vigency_check(requirement_key: str) -> bool:
        return DocumentValidityAnalyzer.requires_vigency_check(requirement_key)

    @staticmethod
    def is_non_vigency_document(requirement_key: str) -> bool:
        return not DocumentValidityAnalyzer.requires_vigency_check(requirement_key) and (
            requirement_key.startswith(("sncc_", "garantia_", "muestra_"))
            or requirement_key
            in {
                "cedula_representante",
                "poder_autorizacion",
                "carta_presentacion",
                "estados_financieros",
                "oferta_economica",
                "oferta_tecnica",
                "autorizacion_fabricante",
                "ficha_tecnica",
            }
        )

    def extract_from_text(self, text: str, *, title: str = "", filename: str = "") -> DocumentValidityResult:
        return self.analyzer.analyze_document(
            "certificacion_dgii",
            text=text,
            title=title,
            filename=filename,
        )

    def resolve_requirement_match(
        self,
        requirement_key: str,
        *,
        text: str = "",
        title: str = "",
        filename: str = "",
        content: bytes | None = None,
        document_id: str | None = None,
    ) -> tuple[str, date | None, str, str | None]:
        status, valid_until, vigency_status, note, _ = self.analyzer.resolve_requirement_match(
            requirement_key,
            text=text,
            title=title,
            filename=filename,
            content=content,
            document_id=document_id,
        )
        return status, valid_until, vigency_status, note
