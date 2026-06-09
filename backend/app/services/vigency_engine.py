"""Motor de vigencias — Corporate Knowledge (Fase 7.2)."""

from __future__ import annotations

from datetime import date, timedelta

from app.config import settings


class VigencyEngine:
    VIGENTE = "vigente"
    PROXIMO = "proximo_a_vencer"
    VENCIDO = "vencido"
    SIN_FECHA = "sin_fecha"

    def classify(self, valid_until: date | None, *, warning_days: int | None = None) -> str:
        if not valid_until:
            return self.SIN_FECHA
        today = date.today()
        warning = warning_days if warning_days is not None else settings.knowledge_vigency_warning_days
        if valid_until < today:
            return self.VENCIDO
        if valid_until <= today + timedelta(days=warning):
            return self.PROXIMO
        return self.VIGENTE

    def alert_for_status(self, *, title: str, document_type: str, status: str, valid_until: date | None) -> dict | None:
        if status == self.VENCIDO:
            return {
                "alert_type": "vencido",
                "severity": "high",
                "title": f"Documento vencido: {title}",
                "message": f"{document_type.upper()} vencido"
                + (f" ({valid_until.isoformat()})" if valid_until else ""),
            }
        if status == self.PROXIMO:
            return {
                "alert_type": "proximo_vencimiento",
                "severity": "medium",
                "title": f"Próximo a vencer: {title}",
                "message": f"{document_type.upper()} vence el {valid_until.isoformat()}" if valid_until else title,
            }
        return None
