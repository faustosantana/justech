"""Alertas automáticas del expediente DGCP (Fase 7.3)."""

from __future__ import annotations

import uuid
from datetime import date

from app.models.dgcp_opportunity import DGCPOpportunity


class DGCPBidAlertService:
    def build_alerts(
        self,
        opportunity: DGCPOpportunity,
        checklist: list[dict],
        matches: list[dict],
        *,
        analysis_warnings: list[str] | None = None,
    ) -> list[dict]:
        alerts: list[dict] = []
        for item in checklist:
            status = item.get("status")
            if status == "encontrado_vencido":
                alerts.append(self._alert(
                    "documento_vencido",
                    "high",
                    f"Documento vencido: {item['requirement']}",
                    item.get("recommended_action") or "Renovar antes del cierre",
                    requirement_key=item.get("requirement_key"),
                ))
            elif status in ("requiere_revision", "encontrado_sin_fecha"):
                alerts.append(self._alert(
                    "vigencia_no_verificada",
                    "medium",
                    f"Vigencia no verificada: {item['requirement']}",
                    item.get("notes") or "Validar vigencia manualmente",
                    requirement_key=item.get("requirement_key"),
                ))
            elif status == "faltante":
                alerts.append(self._alert(
                    "requisito_faltante",
                    "high",
                    f"Requisito faltante: {item['requirement']}",
                    item.get("recommended_action") or "Solicitar o registrar",
                    requirement_key=item.get("requirement_key"),
                ))
            elif status == "requiere_completado":
                alerts.append(self._alert(
                    "formulario_pendiente",
                    "medium",
                    f"Formulario / entregable pendiente: {item['requirement']}",
                    "Completar vista previa / generar copia controlada",
                    requirement_key=item.get("requirement_key"),
                ))

        for warning in analysis_warnings or []:
            if "pliego" in warning.lower() or "tdr" in warning.lower():
                alerts.insert(0, self._alert(
                    "pliego_no_analizado",
                    "high",
                    "Pliego/TDR real no analizado",
                    warning,
                ))
            else:
                alerts.append(self._alert(
                    "analisis_parcial",
                    "medium",
                    "Análisis parcial detectado",
                    warning,
                ))

        if opportunity.deadline:
            days = (opportunity.deadline - date.today()).days
            if days <= 7:
                alerts.append(self._alert(
                    "fecha_limite",
                    "high",
                    f"Cierre del proceso en {days} día(s)",
                    "Priorizar expediente y revisión final",
                    requirement_key="deadline",
                ))

        critical_missing = sum(
            1 for item in checklist
            if item.get("status") == "faltante"
            and item.get("requirement_key") in (
                "rpe", "certificacion_tss", "certificacion_dgii", "registro_mercantil"
            )
        )
        if critical_missing:
            alerts.append(self._alert(
                "requisito_critico",
                "high",
                f"{critical_missing} requisito(s) legal(es) crítico(s) pendiente(s)",
                "Resolver antes de marcar listo para revisión",
            ))

        return alerts

    @staticmethod
    def _alert(
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        *,
        requirement_key: str | None = None,
    ) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "alert_type": alert_type,
            "severity": severity,
            "title": title,
            "message": message,
            "requirement_key": requirement_key,
            "resolved": False,
        }
