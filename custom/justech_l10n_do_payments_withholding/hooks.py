"""Post-init: registra la personalización en el catálogo Justech (idempotente)."""
from __future__ import annotations


def post_init_hook(env):
    from odoo.addons.justech_modules.hooks_register import register_from_manifest_hook

    register_from_manifest_hook(env, "justech_l10n_do_payments_withholding")
    env["justech.license.service"].clear_license_cache()
