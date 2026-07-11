# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
"""SMTP corporativo Hellenia: nunca servidor personal (owner_user_id)."""
from odoo import api, models


class IrMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def _hellenia_smtp_marker(self, value):
        return "helleniadr.com" in (value or "").lower()

    def _hellenia_is_corporate_smtp(self):
        self.ensure_one()
        return self._hellenia_smtp_marker(self.smtp_user) or self._hellenia_smtp_marker(
            self.from_filter
        ) or self._hellenia_smtp_marker(self.name)

    @api.model
    def _hellenia_vals_look_corporate(self, vals):
        return any(
            self._hellenia_smtp_marker(vals.get(field))
            for field in ("smtp_user", "from_filter", "name")
        )

    def _hellenia_force_company_wide(self):
        """Quita owner personal para que todos los usuarios usen este SMTP."""
        to_fix = self.filtered(lambda s: s._hellenia_is_corporate_smtp() and s.owner_user_id)
        if to_fix:
            super(IrMailServer, to_fix).write({"owner_user_id": False})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self._hellenia_vals_look_corporate(vals):
                vals["owner_user_id"] = False
        records = super().create(vals_list)
        records._hellenia_force_company_wide()
        return records

    def write(self, vals):
        vals = dict(vals)
        # Impedir reasignar como personal un SMTP Hellenia
        if "owner_user_id" in vals and (
            any(s._hellenia_is_corporate_smtp() for s in self)
            or self._hellenia_vals_look_corporate(vals)
        ):
            vals["owner_user_id"] = False
        res = super().write(vals)
        self._hellenia_force_company_wide()
        return res
