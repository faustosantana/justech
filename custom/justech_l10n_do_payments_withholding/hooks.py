"""Post-init: sincroniza catálogo retenciones por empresa DO."""
from __future__ import annotations


def post_init_hook(env):
    Catalog = env.get("justech.do.withholding.catalog")
    if not Catalog:
        return
    for company in env["res.company"].search([]).filtered(
        lambda c: c.country_id and c.country_id.code == "DO"
    ):
        Catalog.sync_catalog_from_taxes(company)
