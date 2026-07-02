from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    hellenia_payment_reference = fields.Char(string="Referencia")
    hellenia_card_auth = fields.Char(string="Autorización")
    hellenia_card_batch = fields.Char(string="Lote")
    hellenia_check_number = fields.Char(string="Número de cheque")
    hellenia_check_bank_id = fields.Many2one("res.bank", string="Banco del cheque")
    hellenia_check_date = fields.Date(string="Fecha del cheque")

    hellenia_show_card_fields = fields.Boolean(compute="_compute_hellenia_method_flags")
    hellenia_show_check_fields = fields.Boolean(compute="_compute_hellenia_method_flags")

    @api.depends("payment_method_line_id.name")
    def _compute_hellenia_method_flags(self):
        for wiz in self:
            name = (wiz.payment_method_line_id.name or "").lower()
            wiz.hellenia_show_card_fields = "tarjeta" in name
            wiz.hellenia_show_check_fields = "cheque" in name

    @api.onchange("payment_method_line_id")
    def _onchange_payment_method_line_hellenia_journal(self):
        for wiz in self:
            if not wiz.payment_method_line_id or not wiz.payment_method_line_id.journal_id:
                continue
            wiz.journal_id = wiz.payment_method_line_id.journal_id

    def _hellenia_extra_payment_vals(self):
        self.ensure_one()
        vals = {
            "hellenia_payment_reference": self.hellenia_payment_reference,
            "hellenia_card_auth": self.hellenia_card_auth,
            "hellenia_card_batch": self.hellenia_card_batch,
            "hellenia_check_number": self.hellenia_check_number,
            "hellenia_check_bank_id": self.hellenia_check_bank_id.id,
            "hellenia_check_date": self.hellenia_check_date,
        }
        if self.hellenia_payment_reference:
            vals["memo"] = self.hellenia_payment_reference
        return vals

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        vals.update(self._hellenia_extra_payment_vals())
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        vals = super()._create_payment_vals_from_batch(batch_result)
        vals.update(self._hellenia_extra_payment_vals())
        return vals
