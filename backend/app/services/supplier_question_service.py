"""Preguntas al asistente sobre proveedores."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.assistant import AssistantLink, AssistantQueryResponse
from app.schemas.supplier import SupplierQuoteRequest, SupplierSearchRequest
from app.services.business_intent_router import ParsedBusinessQuestion
from app.services.supplier_service import SupplierService


class SupplierQuestionService:
    SUPPLIER_LOOKUP_SIGNALS = (
        "qué proveedor", "que proveedor", "quién vende", "quien vende",
        "a quién le compro", "a quien le compro", "busca proveedor",
        "proveedores de", "proveedor de", "me vende", "vende toners",
        "vende laptops", "licencias microsoft", "donde compro", "dónde compro",
        "solicitar cotización", "solicitar cotizacion", "pedir cotización",
    )

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.suppliers = SupplierService(db, tenant_id, user_id)

    @classmethod
    def has_supplier_directory_signal(cls, question: str) -> bool:
        q = question.lower()
        return any(sig in q for sig in cls.SUPPLIER_LOOKUP_SIGNALS)

    async def answer(
        self, question: str, classified: ParsedBusinessQuestion | None = None
    ) -> AssistantQueryResponse | None:
        if not self.has_supplier_directory_signal(question) and not (
            classified and classified.intent.value == "supplier_query"
        ):
            return None

        await self.suppliers.ensure_base_categories()
        search = await self.suppliers.search(SupplierSearchRequest(query=question, limit=5))

        if not search.results:
            return AssistantQueryResponse(
                question=question,
                answer=(
                    "No encontré proveedores registrados que coincidan con tu búsqueda. "
                    "Puedes registrar proveedores en Empresas y Proveedores o importarlos desde Excel/CSV."
                ),
                sources=["supplier_directory"],
                query_type="supplier_directory_not_found",
            )

        lines = [f"Encontré {search.total} proveedor(es) recomendado(s):"]
        links: list[AssistantLink] = []

        for idx, match in enumerate(search.results[:5], start=1):
            s = match.supplier
            contact = s.primary_contact or s.email or "—"
            wa = s.whatsapp or s.phone or "—"
            cats = ", ".join(c.name for c in s.categories) or s.category or "—"
            brands = ", ".join(s.brands[:5]) if s.brands else "—"
            lines.append(
                f"\n{idx}. **{s.name}** ({match.confidence})"
                f"\n   • Contacto: {contact}"
                f"\n   • WhatsApp/tel: {wa}"
                f"\n   • Categorías: {cats}"
                f"\n   • Marcas: {brands}"
            )
            if match.recommendation_reason:
                lines.append(f"   • Motivo: {match.recommendation_reason}")
            if s.last_quote_at:
                lines.append(f"   • Última cotización: {s.last_quote_at.strftime('%Y-%m-%d')}")
            if s.price_lists_count:
                lines.append(f"   • Listas de precios: {s.price_lists_count}")
            links.append(
                AssistantLink(label=s.name, url=f"/empresas/{s.id}", type="supplier")
            )

        if search.interpreted_categories:
            lines.append(f"\nCategorías interpretadas: {', '.join(search.interpreted_categories)}")

        quote_signals = ("cotización", "cotizacion", "precio", "whatsapp", "correo")
        if any(sig in question.lower() for sig in quote_signals) and search.results:
            top = search.results[0].supplier
            products = search.interpreted_categories or search.interpreted_brands or ["productos solicitados"]
            quote = await self.suppliers.request_quote(
                top.id,
                SupplierQuoteRequest(products=products, channel="both"),
            )
            if quote and quote.whatsapp_message:
                lines.append(f"\n**WhatsApp sugerido:** {quote.whatsapp_message}")
            if quote and quote.email_body:
                lines.append(f"\n**Correo sugerido:**\n{quote.email_body}")

        return AssistantQueryResponse(
            question=question,
            answer="\n".join(lines),
            sources=["supplier_directory"],
            query_type="supplier_directory",
            links=links,
        )
