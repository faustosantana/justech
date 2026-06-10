"""Acciones de navegación y vista rápida para respuestas del Assistant."""

from __future__ import annotations

from app.services.odoo_url_helper import (
    build_jaios_path,
    build_odoo_url_for_entity,
)


def build_customer_suggested_actions(customer_name: str, customer_id: int | str | None = None) -> list[dict[str, str]]:
    """Acciones sugeridas post-respuesta de cliente."""
    q_name = customer_name.strip()
    actions: list[dict[str, str]] = [
        {"label": "Ver facturas", "type": "internal_link", "url": f"/search?q={q_name}&type=invoices"},
        {"label": "Ver cotizaciones", "type": "internal_link", "url": f"/search?q={q_name}&type=quotations"},
        {"label": "Ver ventas históricas", "type": "internal_link", "url": f"/search?q={q_name}"},
        {
            "label": "Crear tarea de seguimiento",
            "type": "internal_link",
            "url": f"/tasks?new=1&title=Seguimiento%20{q_name.replace(' ', '%20')}",
        },
    ]
    if customer_id is not None:
        actions.insert(0, {
            "label": "Ver cliente",
            "type": "internal_link",
            "url": f"/odoo/customers/{customer_id}",
        })
    return actions


def build_entity_actions(
    entity_type: str,
    entity_id: int | str,
    *,
    label: str | None = None,
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    internal = build_jaios_path(entity_type, entity_id)
    if internal:
        actions.append({
            "label": "Ver en JAIOS",
            "type": "internal_link",
            "url": internal,
        })

    external = build_odoo_url_for_entity(entity_type, entity_id)
    if external:
        actions.append({
            "label": "Ver en Odoo",
            "type": "external_link",
            "url": external,
        })

    actions.append({
        "label": "Vista rápida",
        "type": "quick_view",
        "entity_type": entity_type,
        "entity_id": str(entity_id),
    })
    return actions


def table_row(
    cells: list[str],
    *,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
) -> dict:
    row: dict = {"cells": cells}
    if entity_type and entity_id is not None:
        row["entity_type"] = entity_type
        row["entity_id"] = str(entity_id)
        row["actions"] = build_entity_actions(entity_type, entity_id)
    return row
