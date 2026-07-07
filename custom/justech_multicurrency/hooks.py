"""Install hooks — Justech Multimoneda."""
from __future__ import annotations

import logging

from psycopg2 import IntegrityError

_logger = logging.getLogger(__name__)

AUDIT_MODELS = (
    ("justech.multicurrency.policy", "Política multimoneda Justech", True),
    ("res.currency.rate", "Tasas de cambio", True),
    ("product.pricelist", "Listas de precios comerciales", False),
)


def post_init_hook(env):
    _register_justech_module(env)
    _ensure_company_policies(env)
    _ensure_audit_rules(env)
    _restrict_pricelist_menus(env)


def _restrict_pricelist_menus(env):
    group = env.ref("justech_multicurrency.group_justech_multicurrency_manager", raise_if_not_found=False)
    if not group:
        return
    for xmlid in (
        "product.menu_product_pricelist",
        "sale.menu_product_pricelist_main",
        "sale.menu_sale_pricelist",
        "sale.menu_product_pricelist",
    ):
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            menu.sudo().write({"group_ids": [(6, 0, group.ids)]})


def _register_justech_module(env):
    try:
        from odoo.addons.justech_modules.hooks_register import register_from_manifest_hook

        register_from_manifest_hook(env, "justech_multicurrency")
    except ImportError:
        pass


def _ensure_company_policies(env):
    Policy = env["justech.multicurrency.policy"].sudo()
    for company in env["res.company"].search([]):
        if not Policy.search([("company_id", "=", company.id)], limit=1):
            Policy.create_default_for_company(company)


def _ensure_audit_rules(env):
    if "justech.audit.rule" not in env:
        return
    Rule = env["justech.audit.rule"].sudo().with_context(active_test=False)
    for model_name, label, active in AUDIT_MODELS:
        if model_name not in env:
            continue
        model = env["ir.model"].search([("model", "=", model_name)], limit=1)
        if not model:
            continue
        rule = Rule.search([("model_id", "=", model.id)], limit=1)
        if rule:
            if rule.name != label or rule.active != active:
                rule.write({"name": label, "active": active})
            continue
        try:
            with env.cr.savepoint():
                Rule.create({"name": label, "model_id": model.id, "active": active})
        except IntegrityError:
            _logger.debug("Audit rule already exists for %s", model_name)
