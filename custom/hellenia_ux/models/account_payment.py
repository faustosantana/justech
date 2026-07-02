from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    hellenia_payment_reference = fields.Char(string="Referencia")
    hellenia_card_auth = fields.Char(string="Autorización")
    hellenia_card_batch = fields.Char(string="Lote")
    hellenia_check_number = fields.Char(string="Número de cheque")
    hellenia_check_bank_id = fields.Many2one("res.bank", string="Banco del cheque")
    hellenia_check_date = fields.Date(string="Fecha del cheque")

    hellenia_is_card = fields.Boolean(compute="_compute_hellenia_payment_flags")
    hellenia_is_check = fields.Boolean(compute="_compute_hellenia_payment_flags")
    hellenia_is_transfer = fields.Boolean(compute="_compute_hellenia_payment_flags")
    hellenia_is_cash = fields.Boolean(compute="_compute_hellenia_payment_flags")

    @api.depends("payment_method_line_id.name")
    def _compute_hellenia_payment_flags(self):
        for pay in self:
            name = (pay.payment_method_line_id.name or "").lower()
            pay.hellenia_is_card = "tarjeta" in name
            pay.hellenia_is_check = "cheque" in name
            pay.hellenia_is_transfer = "transferencia" in name
            pay.hellenia_is_cash = "efectivo" in name
