"""Inteligencia IA sobre correos M365 — análisis al abrir mensaje."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.m365_intelligence import M365MailIntelligenceResponse, M365SuggestedAction
from app.services.m365_email_classifier import M365EmailClassifier, EMAIL_CLASS_LABELS
from app.services.m365_email_extraction_service import M365EmailExtractionService
from app.services.m365_graph_session import M365GraphSessionService
from integrations.microsoft365.errors import GraphError


PRIORITY_KEYWORDS = {
    "urgente": 90,
    "urgent": 90,
    "asap": 85,
    "inmediato": 85,
    "hoy": 75,
    "plazo": 70,
    "vence": 72,
    "deadline": 78,
}

RISK_KEYWORDS = ("rechazo", "penalidad", "incumplimiento", "demanda", "cancelación", "cancelacion", "multa")
OPPORTUNITY_KEYWORDS = ("oportunidad", "licitación", "licitacion", "cotización", "cotizacion", "contrato", "adjudicación")


class M365MailIntelligenceService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._sessions = M365GraphSessionService(db, tenant_id, user_id)
        self._classifier = M365EmailClassifier()
        self._extractor = M365EmailExtractionService()

    async def analyze_message(self, message_id: str, *, account_id: uuid.UUID | None = None) -> M365MailIntelligenceResponse | None:
        try:
            sess = await self._sessions.session_for_account(account_id)
            msg = await sess.client.outlook.get_message(message_id)
        except GraphError:
            return None
        if not msg or not msg.id:
            return None

        body = msg.body_text or msg.preview or ""
        att_names = [a.name for a in msg.attachments if a.name]
        classification = self._classifier.classify(
            subject=msg.subject,
            body=body,
            sender_email=msg.sender,
            attachment_names=att_names,
        )
        extracted = self._extractor.extract(
            subject=msg.subject,
            body=body,
            sender_email=msg.sender,
            sender_name=msg.sender_name,
            attachment_texts=[(n, n) for n in att_names],
        )

        combined = f"{msg.subject} {body}".lower()
        priority = 50
        for kw, score in PRIORITY_KEYWORDS.items():
            if kw in combined:
                priority = max(priority, score)
        if classification.classification == "licitacion":
            priority = max(priority, 80)

        sentiment = "neutral"
        if any(w in combined for w in ("gracias", "excelente", "felicit")):
            sentiment = "positive"
        elif any(w in combined for w in ("problema", "reclamo", "queja", "error", "retraso")):
            sentiment = "negative"

        risks = [kw for kw in RISK_KEYWORDS if kw in combined]
        opportunities = [kw for kw in OPPORTUNITY_KEYWORDS if kw in combined]
        if classification.classification == "licitacion":
            opportunities.append("licitación detectada")

        actions = self._suggest_actions(classification.classification, extracted)
        summary = self._build_summary(msg.subject, classification.classification, extracted)

        return M365MailIntelligenceResponse(
            message_id=msg.id,
            classification=classification.classification,
            classification_label=EMAIL_CLASS_LABELS.get(classification.classification, classification.classification),
            classification_confidence=classification.confidence,
            matched_signals=classification.matched_signals,
            summary=summary,
            sentiment=sentiment,
            priority_score=priority,
            priority_label="Alta" if priority >= 75 else "Media" if priority >= 55 else "Normal",
            vendor=extracted.get("vendor"),
            client=extracted.get("client"),
            amount=extracted.get("amount"),
            currency=extracted.get("currency"),
            dgcp_process_code=extracted.get("dgcp_process_code"),
            products=extracted.get("products") or [],
            document_type=extracted.get("document_type"),
            dates=extracted.get("dates") or [],
            risks=risks,
            opportunities=opportunities,
            suggested_actions=actions,
        )

    def _build_summary(self, subject: str, classification: str, extracted: dict) -> str:
        parts = [subject[:120]]
        if extracted.get("vendor"):
            parts.append(f"Proveedor: {extracted['vendor']}")
        if extracted.get("client"):
            parts.append(f"Cliente: {extracted['client']}")
        if extracted.get("dgcp_process_code"):
            parts.append(f"DGCP: {extracted['dgcp_process_code']}")
        if extracted.get("amount"):
            parts.append(f"Monto: {extracted.get('currency', 'USD')} {extracted['amount']}")
        label = EMAIL_CLASS_LABELS.get(classification, classification)
        return f"{label}. " + " · ".join(parts)

    def _suggest_actions(self, classification: str, extracted: dict) -> list[M365SuggestedAction]:
        actions: list[M365SuggestedAction] = [
            M365SuggestedAction(id="summarize", label="Resumir", action_type="ai"),
            M365SuggestedAction(id="search_related", label="Buscar correos relacionados", action_type="search"),
        ]
        if classification in ("cotizacion_proveedor", "catalogo", "ficha_tecnica"):
            actions.append(M365SuggestedAction(id="search_prices", label="Buscar precios", action_type="prices", href="/prices"))
        if classification == "licitacion" or extracted.get("dgcp_process_code"):
            actions.append(M365SuggestedAction(id="create_bid", label="Crear licitación", action_type="dgcp", href="/dgcp"))
        if extracted.get("client"):
            actions.append(M365SuggestedAction(id="create_client", label="Ver cliente", action_type="odoo", href="/odoo"))
        actions.extend(
            [
                M365SuggestedAction(id="create_task", label="Crear tarea", action_type="task", href="/tasks"),
                M365SuggestedAction(id="save_repo", label="Guardar en repositorio", action_type="repository"),
            ]
        )
        return actions
