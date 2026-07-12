import hashlib
import secrets

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class JustechEcfApiToken(models.Model):
    _name = "justech.ecf.api.token"
    _description = "Token API Justech e-CF"
    _order = "id desc"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_ids = fields.Many2many("res.company", string="Empresas autorizadas", required=True)
    scopes = fields.Char(
        default="ecf.read,ecf.write,ecf.receive",
        help="Scopes separados por coma: ecf.read,ecf.write,ecf.receive,ecf.admin",
    )
    key_hash = fields.Char(required=True, copy=False, index=True)
    key_prefix = fields.Char(readonly=True)
    last_used_at = fields.Datetime(readonly=True)
    plain_key_once = fields.Char(
        string="Clave (solo al crear)",
        help="Se muestra una sola vez; no se almacena en claro.",
        readonly=True,
    )

    _sql_constraints = [("key_hash_uniq", "unique(key_hash)", "Hash de API key duplicado.")]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("key_hash"):
                raw = "jecf_" + secrets.token_urlsafe(32)
                vals["key_hash"] = hashlib.sha256(raw.encode()).hexdigest()
                vals["key_prefix"] = raw[:12]
                vals["plain_key_once"] = raw
        return super().create(vals_list)

    def action_rotate(self):
        self.ensure_one()
        raw = "jecf_" + secrets.token_urlsafe(32)
        self.write(
            {
                "key_hash": hashlib.sha256(raw.encode()).hexdigest(),
                "key_prefix": raw[:12],
                "plain_key_once": raw,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Nueva API key"),
                "message": _("Copie ahora: %s") % raw,
                "type": "warning",
                "sticky": True,
            },
        }


class JustechEcfApiAudit(models.Model):
    _name = "justech.ecf.api.audit"
    _description = "Auditoría API e-CF"
    _order = "id desc"

    token_id = fields.Many2one("justech.ecf.api.token", ondelete="set null")
    company_id = fields.Many2one("res.company", index=True)
    action = fields.Char(required=True, index=True)
    success = fields.Boolean(default=True)
    detail = fields.Char()
    ip = fields.Char()
