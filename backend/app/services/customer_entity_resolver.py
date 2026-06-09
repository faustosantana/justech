"""Resolución de clientes con sinónimos, alias y fuzzy matching."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.business_terms import CUSTOMER_ALIASES, expand_customer_terms, normalize_question
from app.services.odoo_service import OdooService

MANUAL_ALIASES: dict[str, list[str]] = {
    **CUSTOMER_ALIASES,
    "capital dbg": ["capital dbg", "capital", "la sociedad", "dbg", "mario dávalos", "mario davalos"],
    "banco ademi": ["banco ademi", "ademi", "banco múltiple ademi", "banco multiple ademi"],
    "farma trix": ["farma trix", "farmatrix", "farma-trix", "farma triz", "farmtrix"],
}


@dataclass
class CustomerMatch:
    label: str
    partner_id: int | None
    partner_name: str | None
    confidence: float
    variants: list[str]
    source: str = "odoo"


@dataclass
class CustomerResolution:
    query: str
    best: CustomerMatch | None
    candidates: list[CustomerMatch]
    needs_confirmation: bool
    message: str


class CustomerEntityResolver:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID):
        self.odoo = OdooService(db, tenant_id, user_id=user_id)

    @staticmethod
    def expand_query(raw: str | None) -> list[str]:
        if not raw:
            return []
        text = normalize_question(raw).lower()
        terms = expand_customer_terms(text)
        for canonical, aliases in MANUAL_ALIASES.items():
            if any(a in text or text in a for a in aliases) or canonical in text:
                terms.extend(aliases)
                terms.append(canonical)
        return list(dict.fromkeys(t for t in terms if t))

    @staticmethod
    def _score(name: str, terms: list[str]) -> float:
        lowered = name.lower()
        if not terms:
            return 0.0
        if any(t == lowered for t in terms):
            return 1.0
        if any(t in lowered or lowered in t for t in terms if len(t) >= 4):
            return 0.85
        tokens = set(re.split(r"[\s,.-]+", lowered))
        overlap = sum(1 for t in terms if t in tokens or any(t in tok for tok in tokens))
        return min(0.8, overlap / max(len(terms), 1))

    async def resolve(self, raw: str | None) -> CustomerResolution:
        terms = self.expand_query(raw)
        if not terms:
            return CustomerResolution(
                query=raw or "",
                best=None,
                candidates=[],
                needs_confirmation=False,
                message="Indica el nombre del cliente.",
            )

        health = await self.odoo.health()
        if not health.connected:
            label = terms[0].title()
            return CustomerResolution(
                query=raw or "",
                best=CustomerMatch(label=label, partner_id=None, partner_name=label, confidence=0.5, variants=terms),
                candidates=[],
                needs_confirmation=False,
                message=f"Odoo no conectado. Buscaré «{label}» cuando esté disponible.",
            )

        resp = await self.odoo.list_customers(search=terms[0], limit=30)
        candidates: list[CustomerMatch] = []
        for item in resp.items:
            name = getattr(item, "name", None) or str(item.get("name", "") if isinstance(item, dict) else "")
            score = self._score(name, terms)
            if score >= 0.45:
                pid = getattr(item, "id", None) or (item.get("id") if isinstance(item, dict) else None)
                candidates.append(
                    CustomerMatch(
                        label=name,
                        partner_id=pid,
                        partner_name=name,
                        confidence=score,
                        variants=terms[:6],
                    )
                )
        candidates.sort(key=lambda c: c.confidence, reverse=True)

        if not candidates:
            label = terms[0].title()
            return CustomerResolution(
                query=raw or "",
                best=CustomerMatch(label=label, partner_id=None, partner_name=label, confidence=0.4, variants=terms),
                candidates=[],
                needs_confirmation=False,
                message=(
                    f"No encontré coincidencias exactas en Odoo para «{raw}». "
                    f"Busqué variantes: {', '.join(terms[:5])}."
                ),
            )

        best = candidates[0]
        needs = (
            len(candidates) > 1
            and best.confidence < 0.92
            and candidates[1].confidence >= best.confidence - 0.08
        )
        if needs:
            opts = ", ".join(c.partner_name for c in candidates[:3] if c.partner_name)
            msg = f"Encontré varias coincidencias ({opts}). ¿Cuál cliente deseas consultar?"
        else:
            msg = f"Encontré coincidencia con «{best.partner_name}». Consultando ventas en Odoo…"

        return CustomerResolution(
            query=raw or "",
            best=best,
            candidates=candidates[:5],
            needs_confirmation=needs,
            message=msg,
        )
