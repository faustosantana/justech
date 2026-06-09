"""URLs seguras de formulario Odoo (sin credenciales)."""

from __future__ import annotations

from app.config import settings

ODOO_MODEL_BY_ENTITY: dict[str, str] = {
    "invoice": "account.move",
    "customer": "res.partner",
    "vendor": "res.partner",
    "product": "product.product",
    "quotation": "sale.order",
    "sale_order": "sale.order",
    "purchase_order": "purchase.order",
    "opportunity": "crm.lead",
}

JAIOS_PATH_BY_ENTITY: dict[str, str] = {
    "invoice": "/odoo/invoices/{id}",
    "customer": "/odoo/customers/{id}",
    "vendor": "/odoo/vendors/{id}",
    "product": "/odoo/products/{id}",
    "quotation": "/odoo",
    "sale_order": "/odoo",
    "purchase_order": "/odoo",
    "opportunity": "/odoo",
    "dgcp": "/dgcp/{id}",
    "task": "/tasks/{id}",
}


def build_odoo_url(model: str, record_id: int | str) -> str | None:
    if not settings.odoo_url:
        return None
    base = settings.odoo_url.rstrip("/")
    return f"{base}/web#id={record_id}&model={model}&view_type=form"


def build_odoo_url_for_entity(entity_type: str, entity_id: int | str) -> str | None:
    model = ODOO_MODEL_BY_ENTITY.get(entity_type)
    if not model:
        return None
    return build_odoo_url(model, entity_id)


def build_jaios_path(entity_type: str, entity_id: int | str) -> str | None:
    template = JAIOS_PATH_BY_ENTITY.get(entity_type)
    if not template or "{id}" not in template:
        return template
    return template.format(id=entity_id)
