# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class JustechRecurringFeeReactivateWizard(models.TransientModel):
    _name = "justech.recurring.fee.reactivate.wizard"
    _description = "Reactivar fee recurrente"

    fee_id = fields.Many2one("justech.recurring.fee", required=True, ondelete="cascade")
    keep_next_date = fields.Boolean(
        string="Conservar fecha de próxima generación",
        default=True,
        help="Si está desmarcado, use la nueva fecha indicada.",
    )
    next_generation_date = fields.Date(string="Nueva fecha de generación")

    def action_confirm(self):
        self.ensure_one()
        fee = self.fee_id
        if fee.state != "paused":
            raise UserError(_("Solo se pueden reactivar fees en estado Pausado."))
        vals = {"state": "active", "last_error": False}
        if not self.keep_next_date:
            if not self.next_generation_date:
                raise UserError(_("Indique la nueva fecha de generación."))
            vals["next_generation_date"] = self.next_generation_date
        fee.write(vals)
        fee.message_post(
            body=_(
                "Fee reactivado. Próxima generación: %(date)s"
            )
            % {"date": fee.next_generation_date}
        )
        return {"type": "ir.actions.act_window_close"}
