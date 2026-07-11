# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)


def post_init_hook(env):
    """Tras instalar: SMTP Hellenia siempre corporativo."""
    _ensure_hellenia_smtp_company_wide(env)


def _ensure_hellenia_smtp_company_wide(env):
    """SMTP @helleniadr.com siempre corporativo (sin owner personal)."""
    servers = env["ir.mail_server"].sudo().search([])
    hellenia = servers.filtered(
        lambda s: "helleniadr.com"
        in f"{s.smtp_user or ''} {s.from_filter or ''} {s.name or ''}".lower()
    )
    owned = hellenia.filtered("owner_user_id")
    if owned:
        owned.write({"owner_user_id": False})
