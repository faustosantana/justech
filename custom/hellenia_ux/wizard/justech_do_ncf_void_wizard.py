from odoo import _, fields, models
from odoo.exceptions import UserError


class JustechDoNcfVoidWizard(models.TransientModel):
    _name = "justech.do.ncf.void.wizard"
    _description = "Anular comprobante fiscal"

    move_id = fields.Many2one("account.move", string="Documento", required=True, readonly=True)
    ncf = fields.Char(related="move_id.justech_do_ncf", string="Número de Comprobante Fiscal")
    void_reason = fields.Text(string="Motivo de anulación", required=True)

    def action_confirm_void(self):
        self.ensure_one()
        reason = (self.void_reason or "").strip()
        if not reason:
            raise UserError(_("Debe indicar el motivo de anulación."))
        self.move_id.write({"justech_do_ncf_void_reason": reason})
        self.move_id.action_void_ncf()
        return {"type": "ir.actions.act_window_close"}
