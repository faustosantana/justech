"""Semantic Resolver Engine — Assistant 3.0 (sinónimos, abreviaciones, entidades)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.business_terms import (
    CUSTOMER_ALIASES,
    clean_entity,
    detect_product_in_text,
    expand_customer_terms,
    normalize_question,
)
from app.services.entity_resolution_engine import EntityResolutionEngine, ResolvedEntity

# Abreviaciones empresariales → expansión en consulta
ABBREVIATIONS: dict[str, str] = {
    r"\boc\b": "orden de compra",
    r"\bpo\b": "purchase order",
    r"\bcxc\b": "cuentas por cobrar",
    r"\bcxp\b": "cuentas por pagar",
    r"\bdgcp\b": "licitaciones dgcp compras públicas",
    r"\bm365\b": "microsoft 365 correo outlook",
    r"\bti\b": "tecnología informática",
    r"\brrhh\b": "recursos humanos",
    r"\bitbis\b": "impuesto itbis",
    r"\brnc\b": "registro nacional contribuyente",
    r"\btss\b": "seguridad social tss",
    r"\bdgii\b": "impuestos internos dgii",
    r"\brpe\b": "registro proveedores estado rpe",
}

CUSTOMER_ROLE_WORDS = (
    "cliente",
    "empresa",
    "cuenta",
    "institución",
    "institucion",
    "banco",
    "compañía",
    "compania",
    "institucion",
)

# Reescrituras de intención antes del router
INTENT_REWRITES: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?i)^(?:ventas|historial|facturaci[oó]n)\s+(?:de|del|a|para)\s+(.+)$"
        ),
        r"¿Qué le hemos vendido a \1?",
    ),
    (
        re.compile(r"(?i)^(?:qu[eé]|que)\s+(?:le\s+)?(?:hemos\s+)?facturad[oa]\s+a\s+(.+)$"),
        r"¿Cuánto le hemos vendido a \1?",
    ),
    (
        re.compile(r"(?i)^(?:mu[eé]strame|muestra)\s+(?:las\s+)?oc\s+pendientes?$"),
        "¿Qué órdenes de compra pendientes hay?",
    ),
    (
        re.compile(r"(?i)^(?:qu[eé]|que)\s+cxc\s+venc(?:en|e)\s+hoy$"),
        "¿Qué facturas vencidas de cuentas por cobrar hay hoy?",
    ),
    (
        re.compile(r"(?i)^revisa\s+dgcp$"),
        "¿Qué licitaciones activas hay en DGCP?",
    ),
]


@dataclass
class SemanticResolution:
    original: str
    normalized: str
    rewritten: str
    abbreviations_applied: list[str] = field(default_factory=list)
    entities: list[ResolvedEntity] = field(default_factory=list)
    customer_label: str | None = None
    customer_terms: list[str] = field(default_factory=list)
    product_label: str | None = None
    product_terms: list[str] = field(default_factory=list)
    intent_hint: str | None = None


class SemanticResolverEngine:
    """Interpreta lenguaje natural empresarial antes del router de intenciones."""

    def __init__(self, db: AsyncSession | None = None, tenant_id: uuid.UUID | None = None):
        self._entity_engine = EntityResolutionEngine(db, tenant_id)

    async def resolve(self, question: str) -> SemanticResolution:
        original = question.strip()
        normalized = normalize_question(original)
        expanded, abbrs = self._expand_abbreviations(normalized)
        rewritten = self._apply_intent_rewrites(expanded)
        rewritten = self._normalize_customer_phrasing(rewritten)

        await self._entity_engine.load()
        entities = self._entity_engine.resolve(rewritten) or self._entity_engine.resolve(normalized)

        customer_label: str | None = None
        customer_terms: list[str] = []
        if entities and entities[0].entity_type in ("cliente", "concepto"):
            ent = entities[0]
            if ent.confidence >= 0.65:
                customer_label = ent.canonical_name
                customer_terms = expand_customer_terms(customer_label)
                if ent.entity_type == "cliente":
                    self._inject_customer_into_rewrite(rewritten, ent)

        product_label, product_terms = detect_product_in_text(rewritten)
        if not product_label:
            product_label, product_terms = detect_product_in_text(normalized)

        intent_hint = self._infer_intent_hint(rewritten)

        return SemanticResolution(
            original=original,
            normalized=normalized,
            rewritten=rewritten,
            abbreviations_applied=abbrs,
            entities=entities,
            customer_label=customer_label,
            customer_terms=customer_terms,
            product_label=product_label,
            product_terms=product_terms,
            intent_hint=intent_hint,
        )

    @staticmethod
    def _expand_abbreviations(text: str) -> tuple[str, list[str]]:
        out = text
        applied: list[str] = []
        for pattern, replacement in ABBREVIATIONS.items():
            if re.search(pattern, out, flags=re.I):
                applied.append(re.sub(r"\\b", "", pattern))
                out = re.sub(pattern, replacement, out, flags=re.I)
        return out.strip(), applied

    @staticmethod
    def _apply_intent_rewrites(text: str) -> str:
        for pattern, repl in INTENT_REWRITES:
            m = pattern.search(text.strip())
            if m:
                return pattern.sub(repl, text.strip()).strip()
        return text.strip()

    @staticmethod
    def _normalize_customer_phrasing(text: str) -> str:
        """'cliente Ademi' / 'empresa Ademi' → incluir nombre canónico si aplica."""
        for canonical, aliases in CUSTOMER_ALIASES.items():
            for alias in aliases:
                for role in CUSTOMER_ROLE_WORDS:
                    pat = rf"(?i)\b{role}\s+{re.escape(alias)}\b"
                    if re.search(pat, text):
                        return re.sub(pat, canonical.title(), text, flags=re.I)
        return text

    @staticmethod
    def _inject_customer_into_rewrite(text: str, entity: ResolvedEntity) -> None:
        pass  # placeholder — rewrite already handled via INTENT_REWRITES

    @staticmethod
    def _infer_intent_hint(text: str) -> str | None:
        lowered = text.lower()
        if any(k in lowered for k in ("vendid", "ventas", "facturad", "compraron")):
            return "sales"
        if any(k in lowered for k in ("debe", "adeuda", "cxc", "cobrar", "vencid")):
            return "finance"
        if any(k in lowered for k in ("licit", "dgcp", "oferta económica", "expediente")):
            return "dgcp"
        if any(k in lowered for k in ("tarea", "pendiente", "vencida")):
            return "tasks"
        if any(k in lowered for k in ("documento", "venc", "rpe", "dgii")):
            return "document"
        return None
