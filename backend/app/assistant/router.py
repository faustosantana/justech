"""AssistantRouter — enrutamiento por fuente (Odoo, DGCP, futuro Hermes/M365)."""

from __future__ import annotations

from enum import Enum


class AssistantSource(str, Enum):
    RULES = "rules"
    ODOO = "odoo"
    DGCP = "dgcp"
    JAIOS = "jaios"
    M365_STUB = "m365_stub"
    WORK = "work"
    ENTERPRISE_SEARCH = "enterprise_search"
    DOCUMENTS = "documents"
    PRICE_INTELLIGENCE = "price_intelligence"
    LOTTERY = "lottery"
    FUTURE_HERMES = "future_hermes"
    FUTURE_M365 = "future_m365"
    FUTURE_QDRANT = "future_qdrant"


class AssistantRouter:
    """Selecciona fuentes disponibles según módulo y tipo de pregunta."""

    FUTURE_SOURCES = frozenset({
        AssistantSource.M365_STUB,
        AssistantSource.FUTURE_HERMES,
        AssistantSource.FUTURE_M365,
        AssistantSource.FUTURE_QDRANT,
    })

    @staticmethod
    def detect_sources(question: str, current_module: str | None) -> list[AssistantSource]:
        lowered = question.lower()
        sources: list[AssistantSource] = [AssistantSource.RULES]

        odoo_keywords = (
            "factura", "cliente", "producto", "cotizacion", "cotización",
            "oportunidad", "proyecto", "proveedor", "vendió", "vendio",
            "vendido", "vendidos", "vendimos", "hemos vendido", "comprado",
            "compramos", "compraron", "cuántas", "cuantas", "cuántos", "cuantos", "cantidad",
            "laptop", "laptops", "monitor", "monitores", "licencia", "licencias",
            "teclado", "teclados", "impresora", "computadora", "precio", "margen",
            "adeuda", "debe", "vencida", "odoo", "costo",
        )
        dgcp_keywords = (
            "dgcp", "licit", "licitar", "proceso", "contratacion",
            "contratación", "vence", "oportunidad pública",
        )
        work_keywords = (
            "tarea", "tareas", "asigna", "asignar", "pendiente", "pendientes",
            "work hub", "notificación operativa", "checklist", "responsable",
            "marieli", "diana", "jennipher", "vencida", "vencidas", "críticas", "criticas",
        )
        search_keywords = (
            "busca", "buscar", "encuentra", "encuentre", "todo sobre", "búsqueda", "busqueda",
            "search", "enterprise search",
        )
        m365_keywords = (
            "microsoft 365", "office 365", "outlook", "sharepoint", "onedrive",
            "teams", "correo", "email", "buzón", "buzon", "calendario", "reunión",
            "reunion", "adjunto", "graph", "m365",
        )
        document_keywords = (
            "documento", "documentos", "pdf", "sncc", "f042", "f047", "rpe",
            "registro mercantil", "expediente", "certificación", "certificacion",
            "formulario", "contrato", "contratos", "resumir", "riesgos tiene",
        )
        price_keywords = (
            "lista de precios", "listas de precios", "me sale mejor", "mejor precio",
            "comparar precio", "alternativas", "quien me sale", "quién me sale",
        )

        lottery_keywords = (
            "lotería", "loteria", "sorteo", "sorteos", "quiniela", "loteka", "leidsa",
            "nacional noche", "nacional día", "nacional dia", "resultado de lotería",
            "resultados de lotería", "boletín", "boletin",
        )
        if any(k in lowered for k in lottery_keywords) or (current_module or "").startswith("/lottery"):
            sources.insert(0, AssistantSource.LOTTERY)

        if any(k in lowered for k in price_keywords) or (current_module or "").startswith("/prices"):
            sources.insert(0, AssistantSource.PRICE_INTELLIGENCE)

        if any(k in lowered for k in document_keywords) or (current_module or "").startswith("/documents"):
            sources.append(AssistantSource.DOCUMENTS)

        if any(k in lowered for k in odoo_keywords) or (current_module or "").startswith("/odoo"):
            sources.append(AssistantSource.ODOO)

        if any(k in lowered for k in dgcp_keywords) or (current_module or "").startswith("/dgcp"):
            sources.append(AssistantSource.DGCP)

        if any(k in lowered for k in m365_keywords) or (current_module or "").startswith("/m365"):
            sources.append(AssistantSource.M365_STUB)

        if any(k in lowered for k in work_keywords) or (current_module or "").startswith(("/work", "/tasks")):
            sources.append(AssistantSource.WORK)

        if any(k in lowered for k in search_keywords) or (current_module or "").startswith("/search"):
            sources.insert(0, AssistantSource.ENTERPRISE_SEARCH)

        if not sources or sources == [AssistantSource.RULES]:
            sources.extend([AssistantSource.ENTERPRISE_SEARCH, AssistantSource.ODOO])

        seen: set[AssistantSource] = set()
        ordered: list[AssistantSource] = []
        for s in sources:
            if s not in seen:
                seen.add(s)
                ordered.append(s)
        return ordered

    @staticmethod
    def source_label(source: AssistantSource) -> str:
        labels = {
            AssistantSource.RULES: "JAIOS",
            AssistantSource.ODOO: "Odoo",
            AssistantSource.DGCP: "DGCP",
            AssistantSource.JAIOS: "JAIOS",
            AssistantSource.FUTURE_HERMES: "Hermes (futuro)",
            AssistantSource.WORK: "Work Operations",
            AssistantSource.ENTERPRISE_SEARCH: "Búsqueda empresarial",
            AssistantSource.DOCUMENTS: "Documentos",
            AssistantSource.LOTTERY: "Lotería IA",
            AssistantSource.PRICE_INTELLIGENCE: "Inteligencia de Precios",
            AssistantSource.M365_STUB: "Microsoft 365",
            AssistantSource.FUTURE_M365: "Microsoft 365 (futuro)",
            AssistantSource.FUTURE_QDRANT: "Enterprise Search (futuro)",
        }
        return labels.get(source, source.value)
