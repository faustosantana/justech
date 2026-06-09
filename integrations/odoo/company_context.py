"""Contexto multiempresa Odoo para consultas read-only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OdooCompanyContext:
    company_id: int
    allowed_company_ids: tuple[int, ...]

    @classmethod
    def from_company_id(cls, company_id: int) -> OdooCompanyContext:
        return cls(company_id=company_id, allowed_company_ids=(company_id,))

    def to_odoo_context(self) -> dict:
        return {
            "allowed_company_ids": list(self.allowed_company_ids),
            "company_id": self.company_id,
        }


# Campo de dominio por modelo para filtrar por empresa
MODEL_COMPANY_FIELD: dict[str, str] = {
    "account.move": "company_id",
    "sale.order": "company_id",
    "sale.order.line": "order_id.company_id",
    "crm.lead": "company_id",
    "project.project": "company_id",
    "purchase.order": "company_id",
    "purchase.order.line": "order_id.company_id",
    "helpdesk.ticket": "company_id",
    "product.product": "company_id",
    "product.template": "company_id",
    "account.move.line": "move_id.company_id",
}


def apply_company_domain(
    domain: list,
    model: str,
    company_id: int | None,
    *,
    include_shared: bool = False,
    company_ids: list[int] | None = None,
) -> list:
    """Añade filtro de empresa al dominio cuando el modelo lo soporta."""
    ids = company_ids or ([company_id] if company_id else [])
    if not ids:
        return domain
    field = MODEL_COMPANY_FIELD.get(model)
    if not field:
        return domain
    if len(ids) == 1:
        cid = ids[0]
        if include_shared and field == "company_id":
            return domain + ["|", (field, "=", False), (field, "=", cid)]
        return domain + [(field, "=", cid)]
    if field == "company_id":
        return domain + [(field, "in", ids)]
    return domain + [(field, "=", ids[0])]
