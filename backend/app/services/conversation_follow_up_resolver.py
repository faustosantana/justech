"""Resuelve preguntas de seguimiento usando contexto conversacional."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.assistant_conversation_context import ConversationEntities
from app.services.business_terms import detect_product_in_text, expand_product_terms


@dataclass
class FollowUpResolution:
    question: str
    was_follow_up: bool
    used_context: dict[str, str | int | None]
    original_question: str


FOLLOW_UP_BUYERS = re.compile(
    r"(?i)^[\s¿]*(?:y\s+)?(?:a\s+qui[eé]n(?:es)?|qui[eé]n(?:es)?)\s+"
    r"(?:se\s+lo\s+)?(?:hemos\s+)?(?:vendid[oa]s?|comprado|vendido|compraron)\??\s*$"
)
FOLLOW_UP_PRICE = re.compile(
    r"(?i)^[\s¿]*(?:y\s+)?(?:a\s+)?(?:qu[eé]\s+precio|en\s+cu[aá]nto|cu[aá]nto\s+cuesta)\??\s*$"
)
FOLLOW_UP_TOP_BUYER = re.compile(
    r"(?i)^[\s¿]*(?:y\s+)?(?:qui[eé]n\s+compr[oó]\s+m[aá]s|el\s+que\s+m[aá]s\s+compr[oó])\??\s*$"
)
FOLLOW_UP_QUANTITY = re.compile(
    r"(?i)^[\s¿]*(?:y\s+)?(?:cu[aá]nt[oa]s?\s+)?(?:hemos\s+)?vendid[oa]s?\??\s*$"
)
FOLLOW_UP_FINANCE_DEBT = re.compile(
    r"(?i)^[\s¿]*(?:y\s+)?(?:cu[aá]nto\s+)?(?:nos\s+)?deben\??\s*$"
)
FOLLOW_UP_FINANCE_INVOICES = re.compile(
    r"(?i)^[\s¿]*(?:y\s+)?(?:las\s+)?facturas\s+vencidas?\??\s*$"
)
FOLLOW_UP_FINANCE_CXC = re.compile(
    r"(?i)^[\s¿]*(?:y\s+)?(?:las\s+)?cxc\??\s*$"
)
FOLLOW_UP_YEAR_ONLY = re.compile(
    r"(?i)^[\s¿]*(?:y\s+)?(?:en\s+)?(?:este\s+a[nñ]o|20\d{2})\??\s*$"
)


def _year_suffix(ctx: ConversationEntities, question: str) -> str:
    from app.services.assistant_conversation_context import ConversationContextStore

    year = ConversationContextStore.detect_year_filter(question) or ctx.year_filter
    if year:
        return f" en {year}"
    if re.search(r"\beste\s+a[nñ]o\b", question.lower()):
        return " este año"
    return ""


def resolve_follow_up(question: str, ctx: ConversationEntities) -> FollowUpResolution:
    q = question.strip()
    original = q
    used: dict[str, str | int | None] = {}
    product = ctx.current_product
    year_note = _year_suffix(ctx, q)

    if not product and not ctx.current_customer and not ctx.current_bid_id:
        return FollowUpResolution(q, False, used, original)

    if ctx.current_customer and FOLLOW_UP_FINANCE_DEBT.match(q):
        resolved = f"¿Cuánto nos debe {ctx.current_customer}?"
        used["customer"] = ctx.current_customer
        return FollowUpResolution(resolved, True, used, original)

    if ctx.current_customer and (FOLLOW_UP_FINANCE_INVOICES.match(q) or FOLLOW_UP_FINANCE_CXC.match(q)):
        resolved = f"¿Qué facturas vencidas tiene {ctx.current_customer}?"
        used["customer"] = ctx.current_customer
        return FollowUpResolution(resolved, True, used, original)

    if product and FOLLOW_UP_BUYERS.match(q):
        resolved = f"¿Qué clientes han comprado {product}{year_note}?"
        used["product"] = product
        return FollowUpResolution(resolved, True, used, original)

    if product and FOLLOW_UP_PRICE.match(q):
        resolved = f"¿En cuánto vendimos {product}{year_note}?"
        used["product"] = product
        return FollowUpResolution(resolved, True, used, original)

    if product and FOLLOW_UP_TOP_BUYER.match(q):
        resolved = f"¿Quién ha comprado más {product}{year_note}?"
        used["product"] = product
        return FollowUpResolution(resolved, True, used, original)

    if product and FOLLOW_UP_QUANTITY.match(q):
        resolved = f"¿Cuántos {product} hemos vendido{year_note}?"
        used["product"] = product
        return FollowUpResolution(resolved, True, used, original)

    if product and FOLLOW_UP_YEAR_ONLY.match(q):
        last = ctx.last_intent or "sales_quantity_query"
        if last in ("buyers_query", "top_buyer_query"):
            resolved = f"¿Quién ha comprado más {product}{year_note or ' este año'}?"
        elif last == "last_price_query":
            resolved = f"¿En cuánto vendimos {product}{year_note or ' este año'}?"
        else:
            resolved = f"¿Cuántos {product} hemos vendido{year_note or ' este año'}?"
        used["product"] = product
        used["year_only"] = True
        return FollowUpResolution(resolved, True, used, original)

    if ctx.current_bid_id and re.search(
        r"(?i)(documentos\s+pide|cu[aá]ndo\s+cierra|presupuesto|participar)", q
    ):
        label = ctx.current_bid_label or "la licitación activa"
        if re.search(r"(?i)documentos", q):
            resolved = f"¿Qué documentos pide {label}?"
        elif re.search(r"(?i)cierra", q):
            resolved = f"¿Cuándo cierra {label}?"
        elif re.search(r"(?i)presupuesto", q):
            resolved = f"¿Cuál es el presupuesto de {label}?"
        else:
            resolved = f"¿Podemos participar en {label}?"
        used["bid"] = ctx.current_bid_id
        return FollowUpResolution(resolved, True, used, original)

    detected_product, _ = detect_product_in_text(q)
    if detected_product and detected_product.lower() not in {
        "quién", "quien", "quiénes", "quienes", "qué", "que", "este", "esta", "año",
    }:
        return FollowUpResolution(q, False, {"detected_product": detected_product}, original)

    return FollowUpResolution(q, False, used, original)


def enrich_sales_parse_with_context(
    question: str,
    ctx: ConversationEntities,
) -> tuple[str | None, list[str], str | None, list[str], int | None]:
    """Inyecta producto/cliente/año del contexto cuando el parse no los detecta."""
    from app.services.assistant_conversation_context import ConversationContextStore

    product_label = ctx.current_product
    product_terms = list(ctx.current_product_terms)
    customer_label = ctx.current_customer
    customer_terms = list(ctx.current_customer_terms)
    year = ctx.year_filter

    detected_year = ConversationContextStore.detect_year_filter(question)
    if detected_year:
        year = detected_year

    detected_product, detected_terms = detect_product_in_text(question)
    if detected_product and detected_product.lower() not in {
        "quién", "quien", "quiénes", "quienes", "qué", "que",
    }:
        product_label = detected_product
        product_terms = detected_terms
    elif product_label and not product_terms:
        product_terms = expand_product_terms(product_label)

    return product_label, product_terms, customer_label, customer_terms, year
