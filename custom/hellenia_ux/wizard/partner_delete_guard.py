# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelleniaPartnerDeleteGuard(models.TransientModel):
    _name = "hellenia.partner.delete.guard"
    _description = "Asistente de eliminación segura de contactos"

    partner_id = fields.Many2one("res.partner", required=True, readonly=True)
    partner_name = fields.Char(related="partner_id.display_name", readonly=True)
    partner_email = fields.Char(related="partner_id.email", readonly=True)
    block_reason = fields.Selection(
        selection=[
            ("company", "Empresa"),
            ("user", "Usuario"),
            ("documents", "Operaciones"),
            ("system", "Sistema"),
        ],
        required=True,
        readonly=True,
    )
    message = fields.Text(readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    user_id = fields.Many2one("res.users", readonly=True)

    show_company_button = fields.Boolean(compute="_compute_buttons")
    show_user_button = fields.Boolean(compute="_compute_buttons")
    show_edit_button = fields.Boolean(compute="_compute_buttons")
    show_archive_button = fields.Boolean(compute="_compute_buttons")

    @api.depends("block_reason")
    def _compute_buttons(self):
        for wiz in self:
            wiz.show_company_button = wiz.block_reason == "company" and bool(wiz.company_id)
            wiz.show_user_button = wiz.block_reason == "user" and bool(wiz.user_id)
            wiz.show_edit_button = wiz.block_reason in ("company", "user", "documents", "system")
            wiz.show_archive_button = wiz.block_reason == "documents"

    def action_open_company(self):
        self.ensure_one()
        if not self.company_id:
            raise UserError(_("No hay empresa relacionada."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Empresa"),
            "res_model": "res.company",
            "res_id": self.company_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_user(self):
        self.ensure_one()
        if not self.user_id:
            raise UserError(_("No hay usuario relacionado."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Usuario"),
            "res_model": "res.users",
            "res_id": self.user_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_edit_partner(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Editar contacto"),
            "res_model": "res.partner",
            "res_id": self.partner_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_archive_partner(self):
        self.ensure_one()
        if self.block_reason != "documents":
            raise UserError(_("Solo se puede archivar desde este asistente cuando hay operaciones relacionadas."))
        self.partner_id.action_archive()
        return {"type": "ir.actions.act_window_close"}

    def action_cancel(self):
        return {"type": "ir.actions.act_window_close"}
