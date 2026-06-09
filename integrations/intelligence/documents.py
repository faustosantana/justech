"""DGCP Document Automation — plantillas futuras (Fase 5+)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DGCPDocumentType(str, Enum):
    SNCC_F_033 = "SNCC.F.033"
    SNCC_F_034 = "SNCC.F.034"
    SNCC_F_042 = "SNCC.F.042"
    SNCC_F_047 = "SNCC.F.047"
    OFERTA_ECONOMICA = "oferta_economica"
    CARTA_COMERCIAL = "carta_comercial"


@dataclass
class DocumentFillRequest:
    """Solicitud de llenado automático — no implementado en Fase 3."""

    document_type: DGCPDocumentType
    opportunity_id: str | None = None
    partner_id: int | None = None
    context: dict = field(default_factory=dict)
