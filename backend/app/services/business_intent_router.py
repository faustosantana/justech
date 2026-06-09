"""BusinessIntentRouter — clasificación de intenciones empresariales."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from app.services.business_terms import (
    clean_entity,
    detect_product_in_text,
    expand_customer_terms,
    expand_product_terms,
    normalize_question,
)
from app.services.sales_question_service import SalesIntent, SalesQuestionService


class BusinessIntent(str, Enum):
    NONE = "none"
    SALES = "sales_query"
    PURCHASE = "purchase_query"
    DGCP = "dgcp_query"
    TASKS = "tasks_query"
    CUSTOMER_FINANCE = "customer_finance_query"
    SUPPLIER = "supplier_query"
    ENTERPRISE_SEARCH = "enterprise_search_query"
    DOCUMENT = "document_query"
    M365 = "m365_query"
    PRICE = "price_query"


@dataclass
class ParsedBusinessQuestion:
    intent: BusinessIntent
    sub_intent: str | None = None
    product_label: str | None = None
    product_terms: list[str] = field(default_factory=list)
    customer_label: str | None = None
    customer_terms: list[str] = field(default_factory=list)
    supplier_label: str | None = None
    assignee_label: str | None = None
    search_term: str | None = None
    has_clear_entity: bool = False


class BusinessIntentRouter:
    M365_SIGNALS = (
        "correo", "correos", "email", "outlook", "adjunto", "adjuntos",
        "buzón", "buzon", "sharepoint", "onedrive",
    )
    DGCP_SIGNALS = ("dgcp", "licit", "licitar", "licitación", "licitacion", "contratacion", "contratación", "oportunidad pública", "pliego", "tdr")
    TASK_SIGNALS = (
        "tarea", "tareas", "pendiente", "pendientes", "vencida", "vencidas",
        "críticas", "criticas", "jennipher", "diana", "marieli", "soporte",
    )
    PURCHASE_SIGNALS = (
        "compramos", "le compramos", "hemos comprado", "comprado en",
        "proveedor nos vendió", "proveedor nos vendio", "nos vendió", "nos vendio",
        "último costo", "ultimo costo", "a quién le compramos", "a quien le compramos",
        "cuánto hemos comprado", "cuanto hemos comprado",
    )
    SUPPLIER_SIGNALS = (
        "qué le hemos comprado", "que le hemos comprado", "qué proveedor",
        "que proveedor", "proveedor vende",
    )
    FINANCE_SIGNALS = (
        "cuánto nos debe", "cuanto nos debe", "cuánto debe", "cuanto debe",
        "adeuda", "facturas vencidas", "oportunidades tiene",
    )
    SEARCH_SIGNALS = ("busca", "buscar", "encuentra", "encuentre", "todo sobre", "búsqueda", "busqueda")
    DOCUMENT_SIGNALS = (
        "documento", "documentos", "pdf", "sncc", "f042", "f047", "rpe",
        "registro mercantil", "expediente", "certificación", "certificacion",
        "formulario", "resumir", "resume este", "riesgos tiene", "documentos faltan",
        "vencen este mes", "cotización emitió", "cotizacion emitio",
        "dgii", "tss", "vigencia", "vigente", "vencidos",
    )
    PRICE_SIGNALS = (
        "lista de precios", "listas de precios", "me sale mejor", "más barata", "mas barata",
        "más barato", "mas barato", "mejor precio", "comparar precio", "alternativas de precio",
        "quien me sale", "quién me sale", "cuál proveedor tiene mejor", "cual proveedor tiene mejor",
    )

    @classmethod
    def classify(cls, question: str) -> ParsedBusinessQuestion:
        q = normalize_question(question)
        lowered = q.lower()

        if cls._is_document_query(lowered):
            return ParsedBusinessQuestion(
                intent=BusinessIntent.DOCUMENT,
                sub_intent=cls._document_sub_intent(lowered),
                search_term=cls._extract_document_term(q),
                has_clear_entity=True,
            )

        if any(sig in lowered for sig in cls.PURCHASE_SIGNALS) or re.search(
            r"(?i)proveedor\s+nos\s+vendi[oó]", lowered
        ):
            product_label, product_terms = cls._extract_purchase_product(q)
            supplier = cls._extract_supplier(q)
            return ParsedBusinessQuestion(
                intent=BusinessIntent.PURCHASE,
                product_label=product_label,
                product_terms=product_terms,
                supplier_label=supplier,
                has_clear_entity=bool(product_label or supplier),
                sub_intent="last_cost" if "costo" in lowered else None,
            )

        if cls._is_odoo_sales(lowered) or SalesQuestionService.has_sales_signal(question):
            sales_parsed = SalesQuestionService.parse(question)
            if sales_parsed.intent != SalesIntent.NONE:
                return ParsedBusinessQuestion(
                    intent=BusinessIntent.SALES,
                    sub_intent=sales_parsed.intent.value,
                    product_label=sales_parsed.product_label,
                    product_terms=sales_parsed.search_terms,
                    customer_label=sales_parsed.customer_label,
                    customer_terms=sales_parsed.customer_terms,
                    has_clear_entity=bool(
                        sales_parsed.search_terms
                        or sales_parsed.customer_label
                        or sales_parsed.intent != SalesIntent.INSUFFICIENT
                    ),
                )
            product_label, product_terms = detect_product_in_text(q)
            if product_label:
                return ParsedBusinessQuestion(
                    intent=BusinessIntent.SALES,
                    sub_intent=SalesIntent.SALES_QUANTITY.value,
                    product_label=product_label,
                    product_terms=product_terms,
                    has_clear_entity=True,
                )

        if cls._is_price_query(lowered):
            product_label, product_terms = detect_product_in_text(q)
            return ParsedBusinessQuestion(
                intent=BusinessIntent.PRICE,
                product_label=product_label,
                product_terms=product_terms,
                has_clear_entity=True,
                sub_intent="compare" if any(k in lowered for k in ("me sale mejor", "comparar", "alternativas")) else "search",
            )

        if any(sig in lowered for sig in cls.DGCP_SIGNALS) or cls._dgcp_product_query(lowered):
            product_label, product_terms = cls._extract_dgcp_product(q)
            return ParsedBusinessQuestion(
                intent=BusinessIntent.DGCP,
                product_label=product_label,
                product_terms=product_terms,
                has_clear_entity=bool(product_label) or "vence" in lowered or "licit" in lowered,
            )

        search_term = cls._extract_search_term(q)
        if search_term:
            if any(k in search_term.lower() for k in ("correo", "correos", "email", "adjunto", "adjuntos")):
                return ParsedBusinessQuestion(
                    intent=BusinessIntent.M365,
                    search_term=search_term,
                    has_clear_entity=True,
                )
            return ParsedBusinessQuestion(
                intent=BusinessIntent.ENTERPRISE_SEARCH,
                search_term=search_term,
                has_clear_entity=True,
            )

        if any(sig in lowered for sig in cls.M365_SIGNALS) and not cls._is_odoo_sales(lowered):
            return ParsedBusinessQuestion(intent=BusinessIntent.M365, has_clear_entity=True)

        assignee = cls._extract_assignee(q)
        if assignee or (
            any(sig in lowered for sig in cls.TASK_SIGNALS)
            and not any(sig in lowered for sig in cls.DGCP_SIGNALS)
        ):
            if any(sig in lowered for sig in cls.TASK_SIGNALS) or assignee:
                return ParsedBusinessQuestion(
                    intent=BusinessIntent.TASKS,
                    assignee_label=assignee,
                    has_clear_entity=bool(assignee) or "vencida" in lowered or "pendiente" in lowered,
                )

        if any(sig in lowered for sig in cls.FINANCE_SIGNALS):
            customer = cls._extract_customer_from_finance(q)
            return ParsedBusinessQuestion(
                intent=BusinessIntent.CUSTOMER_FINANCE,
                customer_label=customer,
                customer_terms=expand_customer_terms(customer) if customer else [],
                has_clear_entity=bool(customer),
            )

        if any(sig in lowered for sig in cls.SUPPLIER_SIGNALS):
            supplier = cls._extract_supplier(q)
            product_label, product_terms = detect_product_in_text(q)
            return ParsedBusinessQuestion(
                intent=BusinessIntent.SUPPLIER,
                supplier_label=supplier,
                product_label=product_label,
                product_terms=product_terms,
                has_clear_entity=bool(supplier or product_label),
            )

        product_label, product_terms = detect_product_in_text(q)
        if product_label and any(
            sig in lowered for sig in ("vendid", "vendimos", "compraron", "clientes")
        ):
            return ParsedBusinessQuestion(
                intent=BusinessIntent.SALES,
                sub_intent=SalesIntent.SALES_QUANTITY.value,
                product_label=product_label,
                product_terms=product_terms,
                has_clear_entity=True,
            )

        if product_label:
            return ParsedBusinessQuestion(
                intent=BusinessIntent.PRICE,
                product_label=product_label,
                product_terms=product_terms,
                has_clear_entity=True,
                sub_intent="search",
            )

        return ParsedBusinessQuestion(intent=BusinessIntent.NONE)

    @staticmethod
    def _is_odoo_sales(lowered: str) -> bool:
        return any(
            sig in lowered
            for sig in (
                "vendid", "vendimos", "hemos vendido", "le hemos vendido",
                "clientes compraron", "cuánto hemos vendido", "cuanto hemos vendido",
            )
        )

    @staticmethod
    def _dgcp_product_query(lowered: str) -> bool:
        return bool(
            re.search(r"licitaciones?\s+(?:hay\s+)?de\s+", lowered)
            or re.search(r"hay\s+licitaciones?\s+de\s+", lowered)
            or re.search(r"licitaciones?\s+de\s+", lowered)
        )

    @classmethod
    def _is_document_query(cls, lowered: str) -> bool:
        if "todo sobre" in lowered:
            return False
        if any(sig in lowered for sig in cls.DOCUMENT_SIGNALS):
            return True
        if re.search(
            r"(?i)(dónde está|donde esta|muéstrame|muestrame).*(rpe|sncc|registro|certific|contrato|documento)",
            lowered,
        ):
            return True
        if re.search(r"(?i)documentos?\s+(?:de|con|donde)", lowered):
            return True
        if re.search(r"(?i)contratos?\s+de\s+", lowered):
            return True
        if "expediente" in lowered and any(
            k in lowered for k in ("porcentaje", "preparación", "preparacion", "listo", "presentar", "checklist", "pide", "requisito")
        ):
            return False
        if re.search(r"(?i)documentos?\s+.*vencid", lowered):
            return True
        if re.search(r"(?i)tenemos\s+.*vigente", lowered):
            return True
        if "faltan" in lowered and "licit" in lowered:
            return True
        return False

    @classmethod
    def _is_price_query(cls, lowered: str) -> bool:
        from app.services.price_question_service import PriceQuestionService

        if cls._is_odoo_sales(lowered) or any(sig in lowered for sig in cls.PURCHASE_SIGNALS):
            return False
        if any(sig in lowered for sig in cls.DGCP_SIGNALS) or cls._dgcp_product_query(lowered):
            return False
        if any(sig in lowered for sig in cls.PRICE_SIGNALS):
            return True
        if "lista" in lowered and "precio" in lowered:
            return True
        return PriceQuestionService.is_price_question(lowered)

    @staticmethod
    def _document_sub_intent(lowered: str) -> str | None:
        if "sncc" in lowered and ("f042" in lowered or "f047" in lowered):
            return "completion_preview"
        if "faltan" in lowered and "licit" in lowered:
            return "expediente"
        if "vencen" in lowered and ("certific" in lowered or "mes" in lowered):
            return "expirations"
        return "content_search"

    @staticmethod
    def _extract_document_term(question: str) -> str | None:
        patterns = (
            r"(?i)(?:dónde está|donde esta|busca|buscar|muéstrame|muestrame|tenemos)\s+(?:el|la|los|las)?\s*(.+)",
            r"(?i)documentos?\s+(?:de|con|donde aparezca)\s+(.+)",
            r"(?i)contratos?\s+de\s+(.+)",
        )
        for pat in patterns:
            m = re.search(pat, question.strip().rstrip("?"))
            if m:
                term = m.group(1).strip().rstrip("?.")
                if len(term) >= 2:
                    return term
        return None

    @staticmethod
    def _extract_search_term(question: str) -> str | None:
        patterns = (
            r"(?i)busca(?:r)?\s+todo\s+sobre\s+(.+)",
            r"(?i)busca(?:r)?\s+(.+)",
            r"(?i)encuentra(?:r)?\s+(.+)",
            r"(?i)búsqueda\s+de\s+(.+)",
            r"(?i)busqueda\s+de\s+(.+)",
        )
        for pattern in patterns:
            match = re.search(pattern, question.strip())
            if match:
                term = match.group(1).strip().rstrip("?.")
                if len(term) >= 2:
                    return term
        return None

    @staticmethod
    def _extract_assignee(question: str) -> str | None:
        patterns = (
            r"(?i)(?:qué|que)\s+tareas?\s+tiene\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",
            r"(?i)(?:qué|que)\s+tiene\s+pendiente\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",
            r"(?i)pendientes?\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",
            r"(?i)pendiente\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",
        )
        for pat in patterns:
            m = re.search(pat, question)
            if m:
                name = m.group(1).strip()
                if name.lower() not in ("soporte", "hoy", "esta", "semana"):
                    return name
        if re.search(r"(?i)pendiente\s+soporte", question):
            return "soporte"
        return None

    @staticmethod
    def _extract_dgcp_product(question: str) -> tuple[str | None, list[str]]:
        patterns = (
            r"(?i)licitaciones?\s+(?:hay\s+)?de\s+(.+)",
            r"(?i)hay\s+licitaciones?\s+de\s+(.+)",
            r"(?i)licitaciones?\s+de\s+(.+)",
            r"(?i)oportunidades?\s+(?:para\s+)?(?:justech\s+)?(?:de\s+|en\s+)?(.+)",
        )
        for pat in patterns:
            m = re.search(pat, question)
            if m:
                raw = clean_entity(m.group(1))
                if raw:
                    return raw, expand_product_terms(raw)
        return detect_product_in_text(question)

    @staticmethod
    def _extract_purchase_product(question: str) -> tuple[str | None, list[str]]:
        patterns = (
            r"(?i)(?:a\s+qui[eé]n\s+le\s+compramos|le\s+compramos)\s+(.+)",
            r"(?i)qu[eé]\s+proveedor\s+nos\s+vendi[oó]\s+(.+)",
            r"(?i)cu[aá]nto\s+hemos\s+comprado\s+en\s+(.+)",
            r"(?i)[uú]ltimo\s+costo\s+de\s+(.+)",
        )
        for pat in patterns:
            m = re.search(pat, question)
            if m:
                raw = clean_entity(m.group(1))
                if raw:
                    return raw, expand_product_terms(raw)
        return detect_product_in_text(question)

    @staticmethod
    def _extract_supplier(question: str) -> str | None:
        patterns = (
            r"(?i)(?:qué|que)\s+le\s+hemos\s+comprado\s+a\s+(.+)",
            r"(?i)le\s+compramos\s+a\s+(.+)",
            r"(?i)a\s+qui[eé]n\s+le\s+compramos\s+(?:a\s+)?(.+)",
        )
        for pat in patterns:
            m = re.search(pat, question)
            if m:
                return clean_entity(m.group(1))
        return None

    @staticmethod
    def _extract_customer_from_finance(question: str) -> str | None:
        patterns = (
            r"(?i)(?:cu[aá]nto\s+nos\s+debe|cu[aá]nto\s+debe|adeuda)\s+(?:el\s+cliente\s+)?(.+)",
            r"(?i)facturas\s+vencidas\s+(?:de\s+|tiene\s+)?(.+)",
            r"(?i)oportunidades\s+tiene\s+(.+)",
        )
        for pat in patterns:
            m = re.search(pat, question)
            if m:
                return clean_entity(m.group(1))
        return None
