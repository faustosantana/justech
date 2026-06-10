"""Calendario inteligente — sugerencias desde correos M365."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from app.schemas.m365_operative import M365CalendarSuggestion, M365CalendarSuggestionsResponse
from app.models.m365_operative import M365ProcessedEmail


class M365CalendarIntelligenceService:
    def suggest_from_email(self, email: M365ProcessedEmail) -> list[M365CalendarSuggestion]:
        suggestions: list[M365CalendarSuggestion] = []
        extracted = email.extracted_data or {}
        classification = email.classification
        base_date = email.received_at or datetime.now(timezone.utc)

        if classification == "licitacion":
            suggestions.append(
                M365CalendarSuggestion(
                    title=f"Revisión pliego — {extracted.get('dgcp_process_code') or email.subject[:60]}",
                    event_type="dgcp_review",
                    suggested_date=base_date + timedelta(days=1),
                    source_email_id=email.id,
                    related_entity_type="dgcp_opportunity",
                    related_entity_id=str(email.related_dgcp_process_id) if email.related_dgcp_process_id else None,
                    confidence=88,
                )
            )
            suggestions.append(
                M365CalendarSuggestion(
                    title=f"Cierre estimado DGCP — {extracted.get('dgcp_process_code') or 'proceso'}",
                    event_type="dgcp_deadline",
                    suggested_date=base_date + timedelta(days=14),
                    source_email_id=email.id,
                    confidence=75,
                )
            )
        if classification == "orden_compra":
            suggestions.append(
                M365CalendarSuggestion(
                    title=f"Seguimiento OC — {extracted.get('client') or 'cliente'}",
                    event_type="commercial_follow_up",
                    suggested_date=base_date + timedelta(days=2),
                    source_email_id=email.id,
                    confidence=82,
                )
            )
        if classification == "factura_proveedor":
            suggestions.append(
                M365CalendarSuggestion(
                    title=f"Vencimiento factura proveedor — {extracted.get('vendor') or 'proveedor'}",
                    event_type="accounts_payable",
                    suggested_date=base_date + timedelta(days=30),
                    source_email_id=email.id,
                    confidence=70,
                )
            )
        if classification == "invitacion_reunion":
            suggestions.append(
                M365CalendarSuggestion(
                    title=email.subject[:120],
                    event_type="meeting",
                    suggested_date=base_date + timedelta(days=3),
                    source_email_id=email.id,
                    confidence=90,
                )
            )
        return suggestions

    def list_for_emails(self, emails: list[M365ProcessedEmail]) -> M365CalendarSuggestionsResponse:
        items: list[M365CalendarSuggestion] = []
        for email in emails[:20]:
            items.extend(self.suggest_from_email(email))
        return M365CalendarSuggestionsResponse(items=items[:30], total=len(items))
