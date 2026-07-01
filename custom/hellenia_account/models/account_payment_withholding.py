"""Retenciones persistentes en pagos — trazabilidad contable y fiscal."""
from __future__ import annotations

from odoo import api, fields, models


class HelleniaAccountPaymentWithholding(models.Model):
    _name = "hellenia.account.payment.withholding"
    _description = "Retención aplicada en pago"
    _order = "invoice_name, id"

    payment_id = fields.Many2one(
        "account.payment",
        string="Pago",
        required=True,
        ondelete="cascade",
        index=True,
    )
    move_id = fields.Many2one("account.move", string="Factura", index=True, ondelete="set null")
    invoice_name = fields.Char(string="Factura")
    ncf = fields.Char(string="NCF")
    catalog_id = fields.Many2one("hellenia.withholding.catalog", string="Retención")
    withholding_type = fields.Selection(related="catalog_id.withholding_type", store=True)
    label = fields.Char(string="Descripción", required=True)
    base_label = fields.Char(string="Tipo de base")
    base_amount = fields.Monetary(string="Base", currency_field="currency_id")
    rate = fields.Float(string="Porcentaje", digits=(16, 4))
    amount = fields.Monetary(string="Monto retenido", currency_field="currency_id", required=True)
    account_id = fields.Many2one("account.account", string="Cuenta contable")
    move_line_id = fields.Many2one(
        "account.move.line",
        string="Línea contable",
        ondelete="set null",
        help="Línea de asiento del pago que registra esta retención.",
    )
    company_id = fields.Many2one(related="payment_id.company_id", store=True)
    currency_id = fields.Many2one(related="payment_id.currency_id", store=True)


class AccountPaymentWithholding(models.Model):
    _inherit = "account.payment"

    hellenia_applied_amount = fields.Monetary(
        string="Monto aplicado",
        currency_field="currency_id",
        copy=False,
        help="Importe bruto aplicado a la factura antes de retenciones.",
    )
    hellenia_withholding_line_ids = fields.One2many(
        "hellenia.account.payment.withholding",
        "payment_id",
        string="Retenciones aplicadas",
        copy=False,
    )
    hellenia_withholding_total = fields.Monetary(
        compute="_compute_hellenia_withholding_totals",
        string="Total retenido",
        currency_field="currency_id",
        store=True,
    )
    hellenia_net_transfer = fields.Monetary(
        compute="_compute_hellenia_withholding_totals",
        string="Neto transferido",
        currency_field="currency_id",
        store=True,
    )
    hellenia_invoice_display = fields.Char(
        compute="_compute_hellenia_invoice_display",
        string="Facturas afectadas",
    )

    @api.depends("hellenia_withholding_line_ids.amount", "hellenia_applied_amount", "amount")
    def _compute_hellenia_withholding_totals(self):
        for pay in self:
            wh_total = sum(pay.hellenia_withholding_line_ids.mapped("amount"))
            pay.hellenia_withholding_total = wh_total
            if pay.hellenia_applied_amount:
                pay.hellenia_net_transfer = pay.hellenia_applied_amount - wh_total
            else:
                pay.hellenia_net_transfer = pay.amount

    @api.depends(
        "hellenia_withholding_line_ids.invoice_name",
        "hellenia_withholding_line_ids.ncf",
        "reconciled_invoice_ids",
        "reconciled_bill_ids",
    )
    def _compute_hellenia_invoice_display(self):
        for pay in self:
            names = pay.hellenia_withholding_line_ids.mapped("invoice_name")
            if not names:
                moves = pay.reconciled_invoice_ids | pay.reconciled_bill_ids
                names = moves.mapped("name")
            pay.hellenia_invoice_display = ", ".join(filter(None, dict.fromkeys(names)))

    def _hellenia_link_withholding_move_lines(self):
        """Vincula cada retención persistente con su línea de asiento en el pago."""
        for pay in self:
            if not pay.move_id:
                continue
            for wh in pay.hellenia_withholding_line_ids.filtered(lambda w: not w.move_line_id):
                candidates = pay.move_id.line_ids.filtered(
                    lambda l: l.account_id == wh.account_id
                    and abs(abs(l.balance) - wh.amount) < 0.02
                )
                if candidates:
                    wh.move_line_id = candidates[:1]
