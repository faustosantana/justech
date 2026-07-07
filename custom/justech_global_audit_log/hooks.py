"""Install hooks for Justech Global Audit Log."""

import logging

from psycopg2 import IntegrityError

_logger = logging.getLogger(__name__)

DEFAULT_INACTIVE_RULES = (
    ("res.partner", "Contactos"),
    ("sale.order", "Pedidos de venta"),
    ("product.template", "Plantillas de producto"),
    ("account.move", "Facturas y asientos"),
    ("account.payment", "Pagos"),
)


def post_init_hook(env):
    _register_justech_module(env)
    _ensure_default_policy(env)
    _ensure_default_rules(env)


def _ensure_default_policy(env):
    Policy = env["justech.audit.policy"].sudo().with_context(active_test=False)
    if Policy.search([], limit=1):
        return
    Policy.create(
        {
            "name": "Política global (desactivada)",
            "active": False,
            "audit_create": True,
            "audit_write": True,
            "audit_unlink": True,
            "audit_events": True,
            "notes": "Activar manualmente según política del cliente.",
        }
    )


def _register_justech_module(env):
    try:
        from odoo.addons.justech_modules.hooks_register import register_from_manifest_hook

        register_from_manifest_hook(env, "justech_global_audit_log")
    except ImportError:
        pass


def _ensure_default_rules(env):
    Rule = env["justech.audit.rule"].sudo().with_context(active_test=False)
    for model_name, label in DEFAULT_INACTIVE_RULES:
        if model_name not in env:
            continue
        model = env["ir.model"].search([("model", "=", model_name)], limit=1)
        if not model:
            continue
        if Rule.search([("model_id", "=", model.id)], limit=1):
            continue
        try:
            with env.cr.savepoint():
                Rule.create(
                    {
                        "name": label,
                        "model_id": model.id,
                        "active": False,
                    }
                )
        except IntegrityError:
            _logger.debug("Audit rule for %s already exists", model_name)
