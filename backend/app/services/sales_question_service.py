"""Interpretación de preguntas de ventas Odoo — read-only."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.assistant import AssistantCard, AssistantLink, AssistantQueryResponse
from app.schemas.odoo import OdooSaleHistoryItem
from app.services.business_answer_builder import build_business_answer, from_sales_report, links_to_dict
from app.services.business_entity_normalizer import (
    NormalizedCustomer,
    NormalizedProduct,
    format_variants_list,
    normalize_customer,
    normalize_product,
)
from app.services.business_terms import (
    clean_entity,
    detect_product_in_text,
    expand_customer_terms,
    expand_product_terms,
    matches_product_name,
    normalize_question,
)
from app.services.odoo_service import OdooService
from app.services.sales_report_builder import (
    build_sales_report,
    format_date_es,
)

SALES_SIGNALS = (
    "vendido", "vendidos", "vendida", "vendidas", "vendimos", "vendió", "vendio",
    "hemos vendido", "le hemos vendido", "se le vendió", "se le vendio",
    "se han vendido", "compraron", "compró", "compro",
    "ha comprado", "han comprado", "vendido a", "vendida a",
    "cantidad", "cuántas", "cuantas", "cuántos", "cuantos", "cuánto hemos",
    "cuanto hemos", "cuánto le hemos", "cuanto le hemos",
    "monto vendido", "clientes compraron", "quién compró",
    "quien compro", "quién ha comprado", "quien ha comprado", "último precio",
    "ultimo precio", "en cuánto vendimos", "en cuanto vendimos",
)


class SalesIntent(str, Enum):
    NONE = "none"
    SALES_QUANTITY = "sales_quantity_query"
    SALES_AMOUNT = "sales_amount_query"
    BUYERS = "buyers_query"
    TOP_BUYER = "top_buyer_query"
    LAST_PRICE = "last_price_query"
    SALES_TO_CUSTOMER = "sales_to_customer_query"
    CUSTOMER_SALES_LIST = "customer_sales_list_query"
    CUSTOMER_SALES_AMOUNT = "customer_sales_amount_query"
    INSUFFICIENT = "insufficient"


@dataclass
class ParsedSalesQuestion:
    intent: SalesIntent
    product_label: str | None
    search_terms: list[str]
    customer_label: str | None = None
    customer_terms: list[str] = field(default_factory=list)
    product_filter_terms: list[str] = field(default_factory=list)
    product_variants: list[str] = field(default_factory=list)
    customer_variants: list[str] = field(default_factory=list)
    year_filter: int | None = None


class SalesQuestionService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.odoo = OdooService(db, tenant_id, user_id=user_id)

    @staticmethod
    def parse_product_lookup(question: str) -> ParsedSalesQuestion | None:
        detected_label, detected_terms = detect_product_in_text(normalize_question(question))
        if not detected_label or not detected_terms:
            return None
        norm = normalize_product(detected_label)
        terms = norm.search_terms if norm else detected_terms
        product_filter = norm.filter_terms if norm else terms
        product_variants = norm.variants_display if norm else terms[:8]
        product_label = norm.label if norm else detected_label
        return ParsedSalesQuestion(
            SalesIntent.SALES_QUANTITY,
            product_label,
            terms,
            product_filter_terms=product_filter,
            product_variants=product_variants,
        )

    async def answer_product_lookup(
        self,
        question: str,
        *,
        source_labels: list[str] | None = None,
    ) -> AssistantQueryResponse | None:
        parsed = self.parse_product_lookup(question)
        if not parsed:
            return None

        labels = source_labels or ["odoo"]
        health = await self.odoo.health()
        if not health.connected:
            return None

        lines, resolved_customer = await self._fetch_lines(parsed)
        lines = self._filter_by_year(lines, parsed.year_filter)
        if not lines:
            return None

        report = build_sales_report(
            lines=lines,
            product_label=parsed.product_label or "productos",
            company_name=health.active_company_name,
            customer_label=resolved_customer,
            intent=parsed.intent.value,
        )
        answer = self._answer_from_report(parsed, report, resolved_customer)
        links = self._product_links(lines)
        structured = from_sales_report(report, intent="sales_query", source="odoo")
        structured["links"] = links_to_dict(links)

        return AssistantQueryResponse(
            question=question,
            answer=answer,
            sources=labels,
            query_type="sales_query",
            structured_data=structured,
            links=links,
            data={
                "intent": parsed.intent.value,
                "product_label": parsed.product_label,
                "customer_label": resolved_customer,
                "search_terms": parsed.search_terms,
                "year_filter": parsed.year_filter,
                "line_count": len(lines),
                "order_count": len({ln.order_name for ln in lines}),
                "lines": len(lines),
            },
        )

    @staticmethod
    def has_sales_signal(question: str) -> bool:
        lowered = question.lower()
        return any(sig in lowered for sig in SALES_SIGNALS)

    @staticmethod
    def parse(question: str) -> ParsedSalesQuestion:
        q = normalize_question(question)
        lowered = q.lower()

        if not SalesQuestionService.has_sales_signal(question):
            return ParsedSalesQuestion(SalesIntent.NONE, None, [])

        product_raw: str | None = None
        customer_raw: str | None = None
        intent = SalesIntent.INSUFFICIENT

        customer_product_patterns = (
            r"(?i)(.+?)\s+le\s+hemos\s+vendid[oa]\s+a\s+(.+?)\s*$",
            r"(?i)(.+?)\s+se\s+le\s+vendid[oa]\s+a\s+(.+?)\s*$",
            r"(?i)(.+?)\s+vendid[oa]\s+a\s+(.+?)\s*$",
        )
        customer_qty_patterns = (
            r"(?i)cu[aá]ntos+\s+(.+?)\s+le\s+hemos\s+vendid[oa]\s+a\s+(.+?)\s*$",
            r"(?i)cu[aá]ntos+\s+(.+?)\s+hemos\s+vendid[oa]\s+a\s+(.+?)\s*$",
            r"(?i)cu[aá]ntos+\s+(.+?)\s+vendid[oa]s?\s+a\s+(.+?)\s*$",
            r"(?i)cu[aá]ntas+\s+(.+?)\s+le\s+hemos\s+vendid[oa]\s+a\s+(.+?)\s*$",
        )
        customer_list_patterns = (
            r"(?i)(?:qué|que)\s+le\s+hemos\s+vendid[oa]\s+a\s+(.+?)\s*$",
            r"(?i)(?:qué|que)\s+(?:le\s+)?(?:se\s+)?vendid[oa]\s+a\s+(.+?)\s*$",
        )
        customer_amount_patterns = (
            r"(?i)cu[aá]nto\s+le\s+hemos\s+vendid[oa]\s+a\s+(.+?)\s*$",
            r"(?i)cu[aá]nto\s+(?:le\s+)?vendimos\s+a\s+(.+?)\s*$",
        )
        quantity_patterns = (
            r"(?i)cu[aá]ntas?\s+(.+?)\s+(?:hemos\s+)?vendid[oa]s?\s*$",
            r"(?i)cu[aá]ntas?\s+(.+?)\s+se\s+han\s+vendid[oa]s?\s*$",
            r"(?i)cu[aá]ntos?\s+(.+?)\s+vendimos\s*$",
            r"(?i)cu[aá]ntos?\s+(.+?)\s+hemos\s+vendid[oa]s?\s*$",
        )
        amount_patterns = (
            r"(?i)cu[aá]nto\s+hemos\s+vendid[oa]\s+en\s+(.+?)\s*$",
            r"(?i)monto\s+vendid[oa]\s+en\s+(.+?)\s*$",
            r"(?i)total\s+vendid[oa]\s+en\s+(.+?)\s*$",
        )
        buyer_patterns = (
            r"(?i)(?:qué|que)\s+clientes\s+compraron\s+(.+?)\s*$",
            r"(?i)qui[eé]n(?:es)?\s+ha(?:n)?\s+comprado\s+(.+?)\s*$",
            r"(?i)(?:qué|que)\s+clientes\s+han\s+comprado\s+(.+?)\s*$",
        )
        top_buyer_patterns = (
            r"(?i)qui[eé]n(?:es)?\s+ha(?:n)?\s+comprado\s+m[aá]s\s+(.+?)\s*$",
            r"(?i)qui[eé]n\s+compr[oó]\s+m[aá]s\s+(.+?)\s*$",
            r"(?i)(?:qué|que)\s+cliente\s+compr[oó]\s+m[aá]s\s+(.+?)\s*$",
        )
        last_price_patterns = (
            r"(?i)en\s+cu[aá]nto\s+vendimos\s+(?:la\s+[uú]ltima\s+|la\s+ultima\s+|la\s+|el\s+|esta\s+|este\s+)?(.+?)\s*$",
            r"(?i)cu[aá]l\s+fue\s+el\s+[uú]ltimo\s+precio\s+(?:de\s+|del\s+)?(.+?)\s*$",
            r"(?i)[uú]ltimo\s+precio\s+(?:de\s+|del\s+)?(.+?)\s*$",
        )

        for pat in customer_list_patterns:
            m = re.search(pat, q)
            if m:
                customer_raw = m.group(1).strip()
                intent = SalesIntent.CUSTOMER_SALES_LIST
                break

        if intent == SalesIntent.INSUFFICIENT:
            for pat in customer_amount_patterns:
                m = re.search(pat, q)
                if m:
                    customer_raw = m.group(1).strip()
                    intent = SalesIntent.CUSTOMER_SALES_AMOUNT
                    break

        if intent == SalesIntent.INSUFFICIENT:
            for pat in customer_qty_patterns:
                m = re.search(pat, q)
                if m:
                    product_raw = m.group(1).strip()
                    customer_raw = m.group(2).strip()
                    intent = SalesIntent.SALES_TO_CUSTOMER
                    break

        if intent == SalesIntent.INSUFFICIENT:
            for pat in customer_product_patterns:
                m = re.search(pat, q)
                if m:
                    product_raw = m.group(1).strip()
                    customer_raw = m.group(2).strip()
                    if not re.match(r"(?i)^(qué|que|cu[aá]nto|cu[aá]ntas?|cu[aá]ntos?)$", product_raw):
                        intent = SalesIntent.SALES_TO_CUSTOMER
                        break

        if intent == SalesIntent.INSUFFICIENT:
            for pat in quantity_patterns:
                m = re.search(pat, q)
                if m:
                    product_raw = m.group(1).strip()
                    intent = SalesIntent.SALES_QUANTITY
                    break

        if intent == SalesIntent.INSUFFICIENT:
            for pat in amount_patterns:
                m = re.search(pat, q)
                if m:
                    product_raw = m.group(1).strip()
                    intent = SalesIntent.SALES_AMOUNT
                    break

        if intent == SalesIntent.INSUFFICIENT:
            for pat in top_buyer_patterns:
                m = re.search(pat, q)
                if m:
                    product_raw = m.group(1).strip()
                    intent = SalesIntent.TOP_BUYER
                    break

        if intent == SalesIntent.INSUFFICIENT:
            for pat in buyer_patterns:
                m = re.search(pat, q)
                if m:
                    product_raw = m.group(1).strip()
                    intent = SalesIntent.BUYERS
                    break

        if intent == SalesIntent.INSUFFICIENT:
            for pat in last_price_patterns:
                m = re.search(pat, q)
                if m:
                    product_raw = m.group(1).strip()
                    intent = SalesIntent.LAST_PRICE
                    break

        informal_quantity_patterns = (
            r"(?i)(?:hemos\s+)?vendid[oa]s?\s+(.+?)\s*$",
            r"(?i)vendimos\s+(.+?)\s*$",
        )
        if intent == SalesIntent.INSUFFICIENT:
            for pat in informal_quantity_patterns:
                m = re.search(pat, q)
                if m:
                    product_raw = m.group(1).strip()
                    intent = SalesIntent.SALES_QUANTITY
                    break

        informal_customer_product = r"(?i)(.+?)\s+a\s+(.+?)\s*$"
        if intent == SalesIntent.INSUFFICIENT and " a " in lowered:
            m = re.search(informal_customer_product, q)
            if m:
                prod = m.group(1).strip()
                cust = m.group(2).strip()
                if not re.match(r"(?i)^(qué|que|cu[aá]nto|cu[aá]ntas?|cu[aá]ntos?)$", prod):
                    product_raw = prod
                    customer_raw = cust
                    intent = SalesIntent.SALES_TO_CUSTOMER

        if intent == SalesIntent.INSUFFICIENT:
            detected_label, detected_terms = detect_product_in_text(q)
            if detected_label and detected_terms:
                norm = normalize_product(detected_label)
                terms = norm.search_terms if norm else detected_terms
                product_filter = norm.filter_terms if norm else terms
                product_variants = norm.variants_display if norm else terms[:8]
                product_label = norm.label if norm else detected_label
                return ParsedSalesQuestion(
                    SalesIntent.SALES_QUANTITY,
                    product_label,
                    terms,
                    product_filter_terms=product_filter,
                    product_variants=product_variants,
                )

        if intent == SalesIntent.INSUFFICIENT and SalesQuestionService.has_sales_signal(q):
            detected_label, detected_terms = detect_product_in_text(q)
            if detected_label and detected_terms:
                return ParsedSalesQuestion(
                    SalesIntent.SALES_QUANTITY,
                    detected_label,
                    detected_terms,
                )
            return ParsedSalesQuestion(SalesIntent.INSUFFICIENT, None, [])

        product_label = clean_entity(product_raw)
        customer_label = clean_entity(customer_raw)

        norm_product = normalize_product(product_label) if product_label else None
        norm_customer = normalize_customer(customer_label) if customer_label else None

        terms = norm_product.search_terms if norm_product else (expand_product_terms(product_label) if product_label else [])
        customer_terms = norm_customer.search_terms if norm_customer else (expand_customer_terms(customer_label) if customer_label else [])
        product_filter = norm_product.filter_terms if norm_product else terms
        product_variants = norm_product.variants_display if norm_product else terms[:8]
        customer_variants = norm_customer.variants_display if norm_customer else customer_terms[:6]

        if norm_customer:
            customer_label = norm_customer.label
        if norm_product:
            product_label = norm_product.label

        if intent in (SalesIntent.CUSTOMER_SALES_LIST, SalesIntent.CUSTOMER_SALES_AMOUNT) and not customer_label:
            return ParsedSalesQuestion(SalesIntent.INSUFFICIENT, None, [])

        if intent == SalesIntent.SALES_TO_CUSTOMER and (not customer_label or not product_label):
            return ParsedSalesQuestion(SalesIntent.INSUFFICIENT, product_label, terms)

        if intent in (SalesIntent.SALES_QUANTITY, SalesIntent.SALES_AMOUNT, SalesIntent.BUYERS, SalesIntent.LAST_PRICE, SalesIntent.TOP_BUYER):
            if not terms:
                return ParsedSalesQuestion(SalesIntent.INSUFFICIENT, product_label, [])

        year_filter = None
        if re.search(r"\beste\s+a[nñ]o\b", lowered):
            from datetime import datetime, timezone
            year_filter = datetime.now(timezone.utc).year
        else:
            ym = re.search(r"\ben\s+(20\d{2})\b", lowered)
            if ym:
                year_filter = int(ym.group(1))

        label = product_label or ("ventas" if customer_label else "producto")
        return ParsedSalesQuestion(
            intent,
            label,
            terms,
            customer_label,
            customer_terms,
            product_filter,
            product_variants,
            customer_variants,
            year_filter,
        )

    @staticmethod
    def parse_with_context(question: str, ctx) -> ParsedSalesQuestion:
        """Re-parse usando entidades de la conversación activa."""
        from app.services.conversation_follow_up_resolver import resolve_follow_up

        resolution = resolve_follow_up(question, ctx)
        effective = resolution.question if resolution.was_follow_up else question
        parsed = SalesQuestionService.parse(effective)
        if parsed.intent != SalesIntent.INSUFFICIENT:
            return parsed

        from app.services.conversation_follow_up_resolver import enrich_sales_parse_with_context

        product_label, product_terms, customer_label, customer_terms, year = enrich_sales_parse_with_context(
            question, ctx
        )
        if not product_label and not customer_label:
            return parsed

        lowered = question.lower()
        if re.search(r"(?i)compr[oó]\s+m[aá]s|comprado\s+m[aá]s", lowered):
            intent = SalesIntent.TOP_BUYER
        elif any(w in lowered for w in ("precio", "cuánto vendimos", "cuanto vendimos", "en cuánto", "en cuanto")):
            intent = SalesIntent.LAST_PRICE
        elif any(
            w in lowered
            for w in ("cliente", "quién", "quien", "quiénes", "quienes", "a quién", "a quien")
        ):
            intent = SalesIntent.BUYERS
        elif any(w in lowered for w in ("cuánto", "cuanto", "cuántas", "cuantas", "cuántos", "cuantos")):
            intent = SalesIntent.SALES_QUANTITY
        else:
            intent = SalesIntent.SALES_QUANTITY

        norm_product = normalize_product(product_label) if product_label else None
        norm_customer = normalize_customer(customer_label) if customer_label else None
        terms = norm_product.search_terms if norm_product else expand_product_terms(product_label or "")
        customer_terms_out = norm_customer.search_terms if norm_customer else expand_customer_terms(customer_label)
        product_filter = norm_product.filter_terms if norm_product else terms
        product_variants = norm_product.variants_display if norm_product else terms[:8]
        customer_variants = norm_customer.variants_display if norm_customer else customer_terms_out[:6]
        if norm_customer:
            customer_label = norm_customer.label
        if norm_product:
            product_label = norm_product.label

        return ParsedSalesQuestion(
            intent,
            product_label or "producto",
            terms,
            customer_label,
            customer_terms_out,
            product_filter,
            product_variants,
            customer_variants,
            year,
        )

    @staticmethod
    def _needs_fuzzy_customer_resolve(label: str, terms: list[str]) -> bool:
        normalized = label.lower().replace("-", " ").strip()
        fuzzy_markers = ("farma", "farmatrix", "farmtrix", "trix", "dbg", "capital")
        if any(m in normalized for m in fuzzy_markers):
            return True
        if normalized in {"ademi", "la sociedad"} or (
            "ademi" in normalized and "banco" not in normalized
        ):
            return True
        return False

    @staticmethod
    def _filter_by_year(lines: list[OdooSaleHistoryItem], year: int | None) -> list[OdooSaleHistoryItem]:
        if not year:
            return lines
        filtered: list[OdooSaleHistoryItem] = []
        prefix = str(year)
        for ln in lines:
            if ln.order_date and str(ln.order_date).startswith(prefix):
                filtered.append(ln)
        return filtered

    @staticmethod
    def _top_buyer_summary(lines: list[OdooSaleHistoryItem]) -> tuple[str | None, float]:
        totals: dict[str, float] = {}
        for ln in lines:
            partner = ln.partner_name or "Cliente"
            totals[partner] = totals.get(partner, 0.0) + float(ln.product_uom_qty or 0)
        if not totals:
            return None, 0.0
        top = max(totals.items(), key=lambda x: x[1])
        return top[0], top[1]

    @staticmethod
    def _matches_line(line: OdooSaleHistoryItem, parsed: ParsedSalesQuestion) -> bool:
        return matches_product_name(
            line.product_name or "",
            parsed.search_terms,
            filter_terms=parsed.product_filter_terms or None,
        )

    async def _fetch_lines(self, parsed: ParsedSalesQuestion) -> tuple[list[OdooSaleHistoryItem], str | None]:
        resolved_customer: str | None = parsed.customer_label

        if parsed.customer_label:
            lines, partner_name = await self.odoo.search_sales_by_partner_name(
                parsed.customer_label,
                limit=500,
                search_terms=parsed.customer_terms or None,
            )
            if partner_name:
                resolved_customer = partner_name
            if parsed.search_terms:
                lines = [ln for ln in lines if self._matches_line(ln, parsed)]
            return lines, resolved_customer

        lines_resp = await self.odoo.search_sales_by_product_terms(parsed.search_terms, limit=500)
        matched = [ln for ln in lines_resp.items if self._matches_line(ln, parsed)]
        if matched:
            return matched, None
        if lines_resp.items:
            return lines_resp.items, None
        return [], None

    @staticmethod
    def _not_found_response(question: str, parsed: ParsedSalesQuestion) -> AssistantQueryResponse:
        product_variants = format_variants_list(parsed.product_variants or parsed.search_terms)
        customer_part = ""
        if parsed.customer_label:
            customer_variants = format_variants_list(parsed.customer_variants or parsed.customer_terms)
            customer_part = (
                f" para el cliente «{parsed.customer_label}» "
                f"(variantes: {customer_variants})"
            )
        answer = (
            "No encontré información suficiente en las fuentes disponibles.\n\n"
            f"Buscé variantes como {product_variants}{customer_part} en Odoo, "
            "pero no hubo ventas confirmadas."
        )
        structured = build_business_answer(
            intent="sales_query",
            source="odoo",
            summary=answer.split("\n\n")[0],
            metrics=[
                {"label": "Variantes producto", "value": str(len(parsed.product_variants or parsed.search_terms))},
                {"label": "Fuente", "value": "Odoo"},
            ],
            warnings=[f"Variantes buscadas: {product_variants}"],
        )
        return AssistantQueryResponse(
            question=question,
            answer=answer,
            sources=["odoo"],
            query_type="sales_query",
            structured_data=structured,
            data={
                "product_label": parsed.product_label,
                "customer_label": parsed.customer_label,
                "search_terms": parsed.search_terms,
                "product_variants": parsed.product_variants,
                "customer_variants": parsed.customer_variants,
                "lines": 0,
            },
        )

    async def answer(
        self,
        question: str,
        *,
        source_labels: list[str] | None = None,
        conversation_context=None,
    ) -> AssistantQueryResponse | None:
        parsed = self.parse(question)
        if parsed.intent == SalesIntent.INSUFFICIENT and conversation_context is not None:
            parsed = self.parse_with_context(question, conversation_context)
        if parsed.intent == SalesIntent.NONE:
            return None

        labels = source_labels or ["Odoo"]

        if parsed.intent == SalesIntent.INSUFFICIENT:
            if SalesQuestionService.has_sales_signal(question):
                return AssistantQueryResponse(
                    question=question,
                    answer=(
                        "No encontré información suficiente en las fuentes disponibles.\n\n"
                        "Detecté una consulta de ventas, pero necesito un producto o cliente más específico. "
                        "Ejemplo: «¿Cuántos rollos de papel 350 hemos vendido?» o "
                        "«¿Qué le hemos vendido a Farma Trix?»"
                    ),
                    sources=labels,
                    query_type="sales_query",
                )
            return None

        health = await self.odoo.health()
        if not health.connected:
            return AssistantQueryResponse(
                question=question,
                answer="Odoo no está conectado. No puedo consultar el historial de ventas.",
                sources=labels,
                query_type="not_connected",
            )

        if parsed.intent == SalesIntent.LAST_PRICE:
            return await self._answer_last_price(question, parsed, labels, health.active_company_name)

        customer_resolver_msg: str | None = None
        if parsed.customer_label and self._needs_fuzzy_customer_resolve(
            parsed.customer_label, parsed.customer_terms
        ):
            from app.services.customer_entity_resolver import CustomerEntityResolver

            resolution = await CustomerEntityResolver(
                self.db, self.tenant_id, self.user_id
            ).resolve(parsed.customer_label)
            customer_resolver_msg = resolution.message
            if resolution.needs_confirmation:
                opts = "\n".join(
                    f"• {c.partner_name} ({int(c.confidence * 100)}%)"
                    for c in resolution.candidates[:5]
                    if c.partner_name
                )
                return AssistantQueryResponse(
                    question=question,
                    answer=f"{resolution.message}\n\n{opts}\n\nIndica el nombre exacto para continuar.",
                    sources=labels,
                    query_type="sales_query",
                    data={"needs_customer_confirmation": True, "candidates": [
                        {"name": c.partner_name, "id": c.partner_id} for c in resolution.candidates[:5]
                    ]},
                )
            if resolution.best and resolution.best.partner_name:
                parsed.customer_label = resolution.best.partner_name
                parsed.customer_terms = resolution.best.variants or parsed.customer_terms
                if not parsed.customer_variants and resolution.best.variants:
                    parsed.customer_variants = resolution.best.variants[:6]

        lines, resolved_customer = await self._fetch_lines(parsed)
        lines = self._filter_by_year(lines, parsed.year_filter)
        customer_display = resolved_customer or parsed.customer_label

        if parsed.intent == SalesIntent.TOP_BUYER:
            if not lines:
                return self._not_found_response(question, parsed)
            top_name, top_qty = self._top_buyer_summary(lines)
            year_note = f" en {parsed.year_filter}" if parsed.year_filter else ""
            answer = (
                f"El cliente que más compró «{parsed.product_label}»{year_note} fue "
                f"«{top_name}» con {top_qty:g} unidades."
            )
            structured = build_business_answer(
                intent="sales_query",
                source="odoo",
                summary=answer,
                metrics=[
                    {"label": "Cliente top", "value": top_name or "—"},
                    {"label": "Cantidad", "value": f"{top_qty:g}"},
                    {"label": "Producto", "value": parsed.product_label or "—"},
                ],
            )
            return AssistantQueryResponse(
                question=question,
                answer=answer,
                sources=["odoo"],
                query_type="sales_query",
                structured_data=structured,
                links=self._product_links(lines),
                data={
                    "intent": parsed.intent.value,
                    "product_label": parsed.product_label,
                    "customer_label": top_name,
                    "search_terms": parsed.search_terms,
                    "year_filter": parsed.year_filter,
                    "line_count": len(lines),
                },
            )

        if not lines:
            return self._not_found_response(question, parsed)

        report = build_sales_report(
            lines=lines,
            product_label=parsed.product_label or "productos",
            company_name=health.active_company_name,
            customer_label=customer_display,
            intent=parsed.intent.value,
        )

        answer = self._answer_from_report(parsed, report, customer_display)
        links = self._product_links(lines)
        structured = from_sales_report(report, intent="sales_query", source="odoo")
        structured["links"] = links_to_dict(links)
        if customer_resolver_msg and not customer_resolver_msg.endswith("?"):
            warnings = list(structured.get("warnings") or [])
            warnings.insert(0, customer_resolver_msg)
            structured["warnings"] = warnings[:5]

        return AssistantQueryResponse(
            question=question,
            answer=answer,
            sources=["odoo"],
            query_type="sales_query",
            structured_data=structured,
            links=links,
            data={
                "intent": parsed.intent.value,
                "product_label": parsed.product_label,
                "customer_label": customer_display,
                "search_terms": parsed.search_terms,
                "year_filter": parsed.year_filter,
                "line_count": len(lines),
                "order_count": len({ln.order_name for ln in lines}),
            },
        )

    @staticmethod
    def _answer_from_report(
        parsed: ParsedSalesQuestion,
        report: dict,
        customer_display: str | None,
    ) -> str:
        summary = report.get("summary", "")
        if parsed.intent == SalesIntent.SALES_TO_CUSTOMER and customer_display and parsed.product_label:
            return f"Sí. {summary}"
        return summary

    async def _answer_last_price(
        self,
        question: str,
        parsed: ParsedSalesQuestion,
        labels: list[str],
        company_name: str | None,
    ) -> AssistantQueryResponse:
        product_term = " ".join(parsed.search_terms[:3])
        result = await self.odoo.last_price(product_name=product_term)
        if not result.unit_price:
            lines_resp = await self.odoo.search_sales_by_product_terms(parsed.search_terms, limit=50)
            lines = [ln for ln in lines_resp.items if self._matches_line(ln, parsed)]
            if not lines:
                return AssistantQueryResponse(
                    question=question,
                    answer=f"No encontré ventas previas de «{parsed.product_label}» en Odoo.",
                    sources=["odoo"],
                    query_type="sales_query",
                )
            last = lines[0]
            return AssistantQueryResponse(
                question=question,
                answer=(
                    f"Última venta de «{last.product_name}»: {last.unit_price} "
                    f"a {last.partner_name} ({format_date_es(last.order_date)})."
                ),
                sources=["odoo"],
                query_type="sales_query",
                cards=[self._card_from_lines(parsed.product_label, [last], company_name, last_price=last.unit_price)],
                data={"last_line": last.model_dump(mode="json")},
            )

        return AssistantQueryResponse(
            question=question,
            answer=(
                f"Último precio de «{result.product_name or parsed.product_label}»: {result.unit_price} "
                f"({result.partner_name or 'cliente'}, {format_date_es(str(result.order_date) if result.order_date else None)})."
            ),
            sources=["odoo"],
            query_type="sales_query",
            cards=[
                AssistantCard(
                    title="Último precio vendido",
                    subtitle=parsed.product_label,
                    fields={
                        "Precio": str(result.unit_price),
                        "Producto": result.product_name or parsed.product_label or "—",
                        "Cliente": result.partner_name or "—",
                        "Pedido": result.order_name or "—",
                        "Fecha": str(result.order_date) if result.order_date else "—",
                        "Empresa": company_name or "—",
                        "Fuente": "Odoo",
                    },
                )
            ],
            data=result.model_dump(mode="json"),
        )

    @staticmethod
    def _card_from_lines(
        label: str,
        lines: list[OdooSaleHistoryItem],
        company_name: str | None,
        *,
        total_qty: float | None = None,
        last_price: Decimal | None = None,
    ) -> AssistantCard:
        orders = {ln.order_name for ln in lines if ln.order_name}
        fields = {
            "Métrica": f"{total_qty:g} unidades" if total_qty is not None else (str(last_price) if last_price else "—"),
            "Líneas de venta": str(len(lines)),
            "Pedidos": str(len(orders)),
            "Empresa": company_name or "—",
            "Fuente": "Odoo",
        }
        return AssistantCard(title=f"Resumen — {label}", subtitle="Ventas históricas", fields=fields)

    @staticmethod
    def _product_links(lines: list[OdooSaleHistoryItem]) -> list[AssistantLink]:
        links: list[AssistantLink] = []
        seen: set[int] = set()
        for ln in lines:
            if ln.product_id and ln.product_id not in seen:
                seen.add(ln.product_id)
                links.append(
                    AssistantLink(label=ln.product_name, url=f"/odoo/products/{ln.product_id}", type="producto")
                )
            if len(links) >= 5:
                break
        return links
