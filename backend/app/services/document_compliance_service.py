"""Motor de cumplimiento documental — validaciones y alertas."""

from __future__ import annotations

from datetime import date

from app.schemas.document import DocumentComplianceResult


class DocumentComplianceService:
    REQUIRED_CERTS = (
        ("registro_mercantil", "Registro Mercantil"),
        ("certificacion_tss", "Certificación TSS"),
        ("certificacion_dgii", "Certificación DGII"),
        ("rpe", "RPE"),
    )

    def validate(
        self,
        *,
        text: str,
        title: str,
        doc_type: str | None,
        valid_until: date | None,
    ) -> DocumentComplianceResult:
        lowered = f"{title} {text}".lower()
        issues: list[dict[str, str]] = []
        missing: list[str] = []
        expired: list[str] = []

        if any(w in lowered for w in ("sin firma", "falta firma", "no firmado")):
            issues.append({"code": "missing_signature", "message": "Firma faltante detectada en el texto."})

        if valid_until and valid_until < date.today():
            expired.append(f"Vigencia vencida el {valid_until.isoformat()}")
            issues.append({"code": "expired", "message": f"Documento vencido desde {valid_until}."})

        if doc_type in ("sncc", "certificacion_tss", "certificacion_dgii", "rpe", "registro_mercantil"):
            for field in ("rnc", "razón social", "razon social", "representante"):
                if field.replace(" ", "") not in lowered.replace(" ", "") and field not in lowered:
                    if field == "rnc" and "rnc" not in lowered:
                        missing.append("RNC")

        status = "ok"
        if expired:
            status = "expired"
        elif issues:
            status = "warning"
        elif missing:
            status = "incomplete"

        return DocumentComplianceResult(
            status=status,
            issues=issues,
            missing_fields=missing,
            expired_items=expired,
        )

    def build_alert_from_compliance(
        self,
        *,
        doc_id: str,
        title: str,
        compliance: DocumentComplianceResult,
        doc_type: str | None,
    ) -> list[dict]:
        alerts: list[dict] = []
        for item in compliance.expired_items:
            alerts.append({
                "document_id": doc_id,
                "alert_type": "expired",
                "severity": "critical",
                "title": f"Vencido: {title}",
                "message": item,
            })
        if doc_type in ("certificacion_tss", "certificacion_dgii", "rpe", "registro_mercantil"):
            for issue in compliance.issues:
                if issue.get("code") == "expired":
                    label = dict(self.REQUIRED_CERTS).get(doc_type, doc_type)
                    alerts.append({
                        "document_id": doc_id,
                        "alert_type": "certification_expired",
                        "severity": "critical",
                        "title": f"{label} vencido",
                        "message": issue.get("message", ""),
                    })
        return alerts
